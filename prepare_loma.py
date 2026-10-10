#!/usr/bin/env python3
"""Prepare all authoritative Loma geometry and declared model inputs, no rays."""
import argparse
import bisect
import csv
import datetime
import hashlib
import json
import math
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent
GEOMETRY=ROOT/'data/authoritative/loma_prieta'
PROFILES={'lom':([0,2,6.7,24,26],[3,4.95,5.94,6.64,8]),
          'lon':([0,2.5,8.9,24,26],[2.53,5.44,6.29,6.69,7.98])}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    with path.open(newline='') as f:
        reader=csv.DictReader(f);return reader.fieldnames,list(reader)
def write(path,header,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=header,lineterminator='\n');w.writeheader();w.writerows(rows)
def profile_value(name,z):
    depth,velocity=PROFILES[name]
    if z<=0:return velocity[0] # Explicit constant extension above the geoid.
    k=min(len(depth)-2,bisect.bisect_right(depth,z)-1)
    return velocity[k]+(velocity[k+1]-velocity[k])*(z-depth[k])/(depth[k+1]-depth[k])
def sandwich(x):
    if x<=0:return 6.
    if x<1:return 6.-2*x
    if x<=5:return 4.
    if x<6:return x-1.
    return 5.+(x-6.)/32. if x<38 else 6.
def distance(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile',choices=sorted(PROFILES),required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    out=ROOT/a.output
    out.relative_to(ROOT)
    if out.exists():raise RuntimeError('Use a new output directory; existing inputs/results are preserved')
    event_header,events=read(GEOMETRY/'selected_events.csv')
    station_header,stations=read(GEOMETRY/'selected_channels.csv')
    if len(events)!=724 or len(stations)!=52:raise RuntimeError('Authoritative geometry count changed')
    if len({r['event_resource_id'] for r in events})!=724:raise RuntimeError('Duplicate event identity')
    station_key=lambda r:(r['channel_seed_id'],r['metadata_epoch_start'],r['metadata_epoch_end'])
    if len({station_key(r) for r in stations})!=52:raise RuntimeError('Duplicate receiver epoch')
    raw_sources={}
    for r in events+stations:
        name,expected=r['source_file'],r['source_sha256']
        if name in raw_sources and raw_sources[name]!=expected:
            raise RuntimeError('Conflicting authoritative source hashes: '+name)
        raw_sources[name]=expected
    for name,expected in raw_sources.items():
        if sha(GEOMETRY/name)!=expected:raise RuntimeError('Pinned authoritative response changed: '+name)
    event_points=[tuple(float(r[k]) for k in ['x_km','y_km','geoid_depth_km']) for r in events]
    receiver_points=[]
    for r in stations:
        if not r['sensor_z_geoid_km'] or r['vertical_coordinate_status'].startswith('ambiguous'):
            raise RuntimeError('Unresolved receiver elevation: '+r['channel_seed_id'])
        receiver_points.append(tuple(float(r[k]) for k in ['x_km','y_km','sensor_z_geoid_km']))
    top=min(-1.,math.floor(min(p[2] for p in receiver_points)))
    x=[-35,-15,0,2,4,6,20,35];xf=sorted(x+[1,5]);y=[-60,-40,-20,0,20,40];z=[top,0,3,7,11,16]
    for point in event_points+receiver_points:
        if not all(lo<=v<=hi for v,lo,hi in zip(point,[x[0],y[0],z[0]],[x[-1],y[-1],z[-1]])):
            raise RuntimeError('Prepared grid does not contain all authoritative geometry')
    pairs=sum(distance(event_points[i],event_points[j])<20 for i in range(724) for j in range(i+1,724))
    if pairs!=152834:raise RuntimeError('Pair selection changed')
    out.mkdir(parents=True)
    coordinate_fields=['id','x','y','z','t']
    extra=['coordinate_basis','origin_resource_id_basis','simulation_origin_time_basis']
    event_rows=[]
    for i,(r,point) in enumerate(zip(events,event_points)):
        row=dict(r,id=i,x=point[0],y=point[1],z=point[2],t=0)
        row.update(coordinate_basis='catalog-defined simulation truth',
                   origin_resource_id_basis='provider catalog geometry reference, not a simulated pick/origin identifier',
                   simulation_origin_time_basis='truth t=0; initial/inverted t is a simulated correction in seconds')
        event_rows.append(row)
    write(out/'truth_events.csv',coordinate_fields+event_header+extra,event_rows)
    station_rows=[dict(r,id=k,x=point[0],y=point[1],z=point[2],t=0) for k,(r,point) in enumerate(zip(stations,receiver_points))]
    write(out/'stations.csv',coordinate_fields+station_header,station_rows)
    for name,x_axis,value in [('truth_grid.csv',xf,lambda xx,zz:sandwich(xx)),
                              ('initial_grid.csv',x,lambda xx,zz:profile_value(a.profile,zz))]:
        write(out/name,['x','y','z','v'],[dict(x=xx,y=yy,z=zz,v=value(xx,zz)) for zz in z for yy in y for xx in x_axis])
    # Diagnostic sample only: shortest and longest geometric path at every
    # receiver, deterministic ties by source index. Full simulation stays dense.
    samples=[]
    for k,receiver in enumerate(receiver_points):
        ordered=sorted(range(724),key=lambda i:(distance(event_points[i],receiver),i))
        for reason,i in [('nearest_source',ordered[0]),('farthest_source',ordered[-1])]:
            row={'event':i,'station':k,'diagnostic_selection':reason,'straight_distance_km':distance(event_points[i],receiver)}
            row.update({'source_'+key:value for key,value in event_rows[i].items()})
            row.update({'receiver_'+key:value for key,value in station_rows[k].items()})
            samples.append(row)
    write(out/'ray_samples.csv',list(samples[0]),samples)
    config=ROOT/('configs/loma_'+a.profile+'.cfg')
    shutil.copyfile(str(config),str(out/'run.cfg'))
    (out/'preflight.cfg').write_text(config.read_text()+'\n# Count actual first-iteration matrix without allocation/solve.\nmatrix_preflight_only 1\n')
    (out/'authoritative_geometry').write_text('Provider event/origin/channel identities define simulation geometry; no observed pick roster is claimed.\n')
    manifest={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'scope':'Authoritative geometry/model preparation only; no rays, synthetic picks or inverse model generated',
              'profile':a.profile.upper(),'profile_source':'USGS OFR 93-578 Table 4, pp.17-18, documented gradient adaptation attributed to Dietz and Ellsworth; not verified target start',
              'profile_depth_km':PROFILES[a.profile][0],'profile_vp_km_s':PROFILES[a.profile][1],
              'sampled_grid_depth_km':z,'sampled_grid_vp_km_s':[profile_value(a.profile,v) for v in z],
              'model_assumptions':'Sample tabulated gradient adaptation at target inversion depths; interpolate between these samples in solver; extend its surface velocity constantly above z=0. This resampling does not retain every original gradient break.',
              'counts':{'events':724,'receivers':52,'unique_rays':37648,'strict_below_20km_pairs':pairs,'absolute_rows':37648,'catalog_rows':7947368,'precise_rows':7947368,'total_rows':15932384,'diagnostic_sample_rays':len(samples)},
              'event_order':'Unchanged selected_events.csv order','station_order':'Unchanged selected_channels.csv order; native NSLC and epoch preserved',
              'authoritative_raw_source_sha256':raw_sources,
              'initialization':'simulate creates initial_events.csv with independent Gaussian 0.6 km errors on each coordinate, clamped to the finite grid, plus independent 0.05 s origin corrections. These values are independent assumptions, not recovered target inputs.',
              'random_sequence':'std::mt19937 seed 2003; C++ normal/uniform distributions; all source xyz/time perturbation draws precede station bias and pick-noise draws. Library/compiler build must be frozen for replay.',
              'timing_definition':'T=continuous selected local ray action; Q=0.01*round(T/0.01), C++ halfway away from zero; A=Q+Uniform_station(-0.3,0.3)+Normal_pick(0,0.04). Absolute A; catalog A_i-A_j; precise Q_i-Q_j. Precise rounding difference error can approach 0.01 s, not 0.005 s.',
              'ray_candidate_settings':{'path_spacing_km':.5,'ray_iterations':1000,'fmm_spacing_km':.5,'fmm_order':2,'closed_receiver_seed_cells':True,'diagnostic_refinement_spacing_km':.25},
              'accuracy_status':'Candidate settings require geometry and full-support local flags plus refinement review; known layered near-critical cases can need FMM spacing 0.0625 km. No sufficiency or global-first-arrival claim.',
              'runtime_plan':{'OMP_NUM_THREADS':4,'address_space_limit_GiB':128},
              'mutable_by_simulate':['truth_events.csv (numeric precision and explicit simulation labels)','initial_events.csv (created only after truth-ray gate succeeds)','arrivals.csv (created only after truth-ray gate succeeds)','observations.csv (created only after truth-ray gate succeeds)'],
              'input_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [GEOMETRY/'selected_events.csv',GEOMETRY/'selected_channels.csv',config,ROOT/'prepare_loma.py',ROOT/'reference/specification_notes.md',ROOT/'src/main.cpp',ROOT/'src/core.hpp']},
              'prepared_sha256':{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},
              'native_source_path_base':'Provider source_file values retain their original data/authoritative/loma_prieta-relative base; original raw response files are unchanged.'}
    (out/'preparation_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest['counts'],indent=2))

if __name__=='__main__':main()
