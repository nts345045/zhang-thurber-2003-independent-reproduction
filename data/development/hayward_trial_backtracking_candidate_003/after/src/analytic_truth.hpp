#pragma once

// Explicit analytic truth is a separately validated input. This consumer checks
// the exact model/geometry and every native row, not the reference mathematics
// or cryptographic provenance. The preparation wrapper pins those source and
// artifact hashes. No Ray or local ray-convergence flag is fabricated here.
struct AnalyticTruth {
  Vec times;
  CsvTable references;
};

AnalyticTruth read_analytic_truth(const std::string &bundle, const Grid &truth,
                                const std::vector<Event> &events,
                                const std::vector<Event> &stations) {
  if (truth.x.size()<2 || truth.y.size()<2 || truth.z.size()<2 ||
      truth.v.size()!=size_t(truth.size()))
    throw std::runtime_error("Analytic truth requires a complete finite grid");
  for (const auto *axis : {&truth.x,&truth.y,&truth.z})
    for (size_t n=0;n<axis->size();++n)
      if (!std::isfinite((*axis)[n]) || (n && !((*axis)[n]>(*axis)[n-1])))
        throw std::runtime_error("Analytic truth requires strictly increasing finite axes");
  for (size_t k=0;k<truth.z.size();++k)
    for (size_t j=0;j<truth.y.size();++j)
      for (size_t i=0;i<truth.x.size();++i) {
        double v=truth.v[truth.id(i,j,k)];
        if (!(v>0) || !std::isfinite(v) || v!=truth.v[truth.id(i,0,0)])
          throw std::runtime_error("Analytic truth requires positive x-only nodal velocity");
      }
  auto grid=csv_table(bundle+"/inputs/truth_grid.csv",{"x","y","z","v"});
  if (grid.header.size()!=4 || grid.rows.size()!=truth.v.size())
    throw std::runtime_error("Analytic truth snapshot grid inventory differs");
  std::vector<bool> seen(truth.v.size(),false);
  for (const auto &row:grid.rows) {
    int index[3]; const Vec *axes[]={&truth.x,&truth.y,&truth.z};
    for (int k=0;k<3;++k) {
      double value=csv_double(row[k]);
      auto position=std::lower_bound(axes[k]->begin(),axes[k]->end(),value);
      if (position==axes[k]->end() || *position!=value)
        throw std::runtime_error("Analytic truth snapshot grid coordinate differs");
      index[k]=int(position-axes[k]->begin());
    }
    size_t n=truth.id(index[0],index[1],index[2]);
    if (seen[n] || csv_double(row[3])!=truth.v[n])
      throw std::runtime_error("Analytic truth snapshot has duplicate or different model node");
    seen[n]=true;
  }
  auto source_table=csv_table(bundle+"/inputs/truth_events.csv",{"id","x","y","z","t"});
  auto station_table=csv_table(bundle+"/inputs/stations.csv",{"id","x","y","z","t"});
  auto compare_geometry=[&](const CsvTable &table,const std::vector<Event> &native) {
    if (native.empty() || table.rows.size()!=native.size())
      throw std::runtime_error("Analytic truth geometry count differs");
    for (size_t n=0;n<native.size();++n) {
      const auto &row=table.rows[n];
      P point{csv_double(row[1]),csv_double(row[2]),csv_double(row[3])};
      if (csv_int(row[0])!=int(n) || point!=native[n].p ||
          csv_double(row[4])!=0 || native[n].t!=0 ||
          csv_metadata(table,row,5)!=native[n].metadata || !truth.contains(point))
        throw std::runtime_error("Analytic truth geometry/native metadata/zero origin differs at row "+std::to_string(n));
    }
  };
  compare_geometry(source_table,events);compare_geometry(station_table,stations);
  if (events.size()>size_t(std::numeric_limits<int>::max())/stations.size())
    throw std::runtime_error("Analytic truth pair inventory exceeds supported indices");
  AnalyticTruth result;
  result.references=csv_table(bundle+"/references.csv");
  Strings expected{"pair_index","event","station","reference_complete","reference_valid",
    "candidate_count","near_tie_count","time_s","branch","turning_x_km",
    "source_dx_s_per_km","source_dy_s_per_km","source_dz_s_per_km"};
  for (const auto &name:source_table.header) expected.push_back("source_"+name);
  for (const auto &name:station_table.header) expected.push_back("receiver_"+name);
  if (result.references.header!=expected || result.references.rows.size()!=events.size()*stations.size())
    throw std::runtime_error("Analytic truth reference schema or full pair inventory differs");
  result.times.reserve(result.references.rows.size());
  const double vmin=*std::min_element(truth.v.begin(),truth.v.end());
  const double vmax=*std::max_element(truth.v.begin(),truth.v.end());
  for (size_t n=0;n<result.references.rows.size();++n) {
    const auto &row=result.references.rows[n];size_t i=n/stations.size(),k=n%stations.size();
    if (csv_int(row[0])!=int(n) || csv_int(row[1])!=int(i) || csv_int(row[2])!=int(k) ||
        csv_int(row[3])!=1 || csv_int(row[4])!=1 || csv_int(row[5])<1 || csv_int(row[6])!=1)
      throw std::runtime_error("Analytic truth reference is unordered, incomplete, invalid or tied at pair "+std::to_string(n));
    double time=csv_double(row[7]);
    if (time<0) throw std::runtime_error("Negative analytic travel time");
    bool direct=row[8]=="direct" || row[8]=="flat_direct" || row[8]=="vertical_direct";
    bool outward=row[8]=="turning" || row[8]=="critical_maximum_or_plateau" ||
                  row[8]=="lower_boundary" || row[8]=="upper_boundary";
    if ((!direct&&!outward) || (direct&&!row[9].empty()))
      throw std::runtime_error("Unknown or inconsistent analytic reference branch");
    if (outward) {
      double turn=csv_double(row[9]);
      if (turn<truth.x.front() || turn>truth.x.back())
        throw std::runtime_error("Analytic reference turn lies outside the original finite box");
    }
    for (size_t c=10;c<13;++c) csv_double(row[c]); // Signed finite branch derivatives.
    size_t field=13;
    for (const auto *native : {&source_table.rows[i],&station_table.rows[k]}) {
      for (size_t c=0;c<native->size();++c,++field) {
        bool equal=c<5 ? csv_double(row[field])==csv_double((*native)[c]) : row[field]==(*native)[c];
        if (!equal) throw std::runtime_error("Analytic reference inline native geometry differs at pair "+std::to_string(n));
      }
    }
    double length=norm(events[i].p-stations[k].p),lower=length/vmax,upper=length/vmin;
    double roundoff=64*std::numeric_limits<double>::epsilon()*std::max(1.,upper);
    if (time<lower-roundoff || time>upper+roundoff)
      throw std::runtime_error("Analytic reference violates finite positive-speed action bounds");
    result.times.push_back(time);
  }
  return result;
}

void write_analytic_truth_status(const std::string &dir,const AnalyticTruth &truth) {
  auto status=output(dir+"/simulation_truth_status.csv");
  status<<"truth_mode";
  for (const auto &name:truth.references.header) status<<','<<csv_quote(name);
  status<<'\n';
  for (const auto &row:truth.references.rows) {
    status<<"continuous_layered_snell_reference";
    for (const auto &value:row) status<<','<<csv_quote(value);
    status<<'\n';
  }
  auto mode=output(dir+"/simulation_truth_mode.txt");
  mode<<"truth_mode continuous_layered_snell_reference\n"
        "truth_times Full identified continuous layered reference table; no polygon truth rays computed.\n"
        "validation C++ checks model, full native geometry, complete ordered valid unique-reference rows and finite values.\n"
        "provenance Byte and mathematical-source hashes are checked by the external preparation wrapper.\n"
        "limitation Reference time ranking uses floating-point actions; inverse forward-ray acceptance remains required.\n";
}
