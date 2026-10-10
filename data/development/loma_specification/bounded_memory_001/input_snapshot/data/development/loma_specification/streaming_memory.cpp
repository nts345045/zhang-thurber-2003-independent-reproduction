// Structural memory probe only. NaN slots have no simulated/observed times.
// No observation CSV or ray is generated. Geometry metadata stay in frozen CSVs.
#include "csv.hpp"
#include <array>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <set>
#include <sys/resource.h>

struct NumericDatum {
  int i, j, k, type;
  double value;
  double a_priori_weight = 1;
  int station_j = -1;
};

size_t column(const CsvTable &table, const std::string &name) {
  for (size_t i = 0; i < table.header.size(); ++i)
    if (table.header[i] == name) return i;
  throw std::runtime_error("Missing geometry field: " + name);
}

int main(int argc, char **argv) {
  if (argc != 3) throw std::runtime_error("Usage: streaming_memory EVENTS CHANNELS");
  auto events = csv_table(argv[1]), channels = csv_table(argv[2]);
  std::vector<std::array<double, 3>> points;
  std::set<std::string> event_ids, channel_epochs;
  const auto eid = column(events, "event_resource_id"), oid = column(events, "origin_resource_id");
  const auto x = column(events, "x_km"), y = column(events, "y_km"), z = column(events, "geoid_depth_km");
  const auto nslc = column(channels, "channel_seed_id"), sid = column(channels, "channel_fdsn_source_id");
  const auto begin = column(channels, "metadata_epoch_start"), end = column(channels, "metadata_epoch_end");
  for (const auto &row : events.rows) {
    if (row[eid].empty() || row[oid].empty() || !event_ids.insert(row[eid]).second)
      throw std::runtime_error("Missing/nonunique event identity");
    points.push_back({csv_double(row[x]), csv_double(row[y]), csv_double(row[z])});
  }
  for (const auto &row : channels.rows)
    if (row[nslc].empty() || row[sid].empty() || row[begin].empty() ||
        !channel_epochs.insert(row[nslc] + '\n' + row[begin] + '\n' + row[end]).second)
      throw std::runtime_error("Missing/nonunique native channel epoch");
  std::vector<std::array<int, 2>> pairs;
  double closest = INFINITY;
  for (int i = 0; i < int(points.size()); ++i)
    for (int j = i + 1; j < int(points.size()); ++j) {
      double squared = 0;
      for (int a = 0; a < 3; ++a) squared += std::pow(points[i][a] - points[j][a], 2);
      double distance = std::sqrt(squared);
      closest = std::min(closest, std::abs(distance - 20));
      if (distance < 20) pairs.push_back({i, j});
    }
  const size_t ne = events.rows.size(), ns = channels.rows.size();
  const size_t count = ne * ns + 2 * pairs.size() * ns;
  std::vector<NumericDatum> slots;
  slots.reserve(count);
  auto start = std::chrono::steady_clock::now();
  auto append = [&](int i, int j, int k, int type) {
    slots.push_back({i, j, k, type, std::numeric_limits<double>::quiet_NaN(), 1, -1});
  };
  for (int i = 0; i < int(ne); ++i)
    for (int k = 0; k < int(ns); ++k) append(i, -1, k, 0);
  for (auto pair : pairs)
    for (int k = 0; k < int(ns); ++k) {
      append(pair[0], pair[1], k, 1);
      append(pair[0], pair[1], k, 2);
    }
  std::array<size_t, 3> types{};
  std::vector<unsigned char> used(ne * ns, 0);
  size_t identity_sides = 0;
  uint64_t checksum = 14695981039346656037ULL;
  for (const auto &d : slots) {
    if (!std::isnan(d.value) || d.i < 0 || d.i >= int(ne) || d.k < 0 || d.k >= int(ns) ||
        d.j >= int(ne) || (d.type == 0 ? d.j != -1 : d.j <= d.i))
      throw std::runtime_error("Invalid structural slot");
    const auto &station = channels.rows[d.k];
    if (station[nslc].empty() || station[sid].empty() || station[begin].empty())
      throw std::runtime_error("Lost channel identity");
    for (int i : {d.i, d.j}) if (i >= 0) {
      if (events.rows[i][eid].empty() || events.rows[i][oid].empty())
        throw std::runtime_error("Lost event/origin identity");
      ++identity_sides;
      used[size_t(i) * ns + d.k] = 1;
    }
    ++types[d.type];
    // Ordered, noncryptographic structural checksum; no timing value is hashed.
    for (int field : {d.i, d.j, d.k, d.type})
      for (int byte = 0; byte < 4; ++byte) {
        checksum ^= (uint32_t(field) >> (8 * byte)) & 255;
        checksum *= 1099511628211ULL;
      }
  }
  size_t rays = 0;
  for (auto present : used) rays += present;
  struct rusage usage{};
  if (getrusage(RUSAGE_SELF, &usage)) throw std::runtime_error("Cannot measure peak RSS");
  double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
  std::cout << std::setprecision(17)
            << "{\"sources\":" << ne << ",\"receivers\":" << ns
            << ",\"strict_below_20km_pairs\":" << pairs.size()
            << ",\"row_slots\":" << slots.size() << ",\"numeric_datum_bytes\":" << sizeof(NumericDatum)
            << ",\"numeric_capacity_bytes\":" << slots.capacity() * sizeof(NumericDatum)
            << ",\"absolute_slots\":" << types[0] << ",\"catalog_slots\":" << types[1]
            << ",\"precise_slots\":" << types[2] << ",\"unique_ray_slots\":" << rays
            << ",\"event_identity_sides_checked\":" << identity_sides
            << ",\"closest_to_threshold_km\":" << closest
            << ",\"ordered_index_fnv1a64\":\"" << checksum << "\""
            << ",\"allocation_and_validation_seconds\":" << seconds
            << ",\"linux_peak_rss_kib\":" << usage.ru_maxrss << "}\n";
}
