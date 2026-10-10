#pragma once
#include <cmath>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using Strings = std::vector<std::string>;
using Metadata = std::vector<std::pair<std::string, std::string>>;
struct CsvTable {
  Strings header;
  std::vector<Strings> rows;
};

// RFC 4180 quoting, including commas, escaped quotes, and embedded newlines.
bool csv_record(std::istream &in, Strings &row) {
  row.clear();
  std::string value;
  bool quoted = false, closed = false, started = false;
  for (int next; (next = in.get()) != EOF;) {
    char c = char(next);
    started = true;
    if (quoted) {
      if (c == '"') {
        if (in.peek() == '"') {
          in.get();
          value += '"';
        } else {
          quoted = false;
          closed = true;
        }
      } else {
        value += c;
      }
    } else if (c == ',' || c == '\n' || c == '\r') {
      row.push_back(value);
      value.clear();
      closed = false;
      if (c != ',') {
        if (c == '\r' && in.peek() == '\n')
          in.get();
        return true;
      }
    } else if (c == '"' && value.empty() && !closed) {
      quoted = true;
    } else {
      if (closed || c == '"')
        throw std::runtime_error("Malformed CSV quoting");
      value += c;
    }
  }
  if (quoted)
    throw std::runtime_error("Unterminated CSV quote");
  if (started)
    row.push_back(value);
  return started;
}

CsvTable csv_table(const std::string &path, const Strings &prefix = {}) {
  std::ifstream f(path);
  if (!f)
    throw std::runtime_error("Cannot read " + path);
  CsvTable table;
  if (!csv_record(f, table.header))
    throw std::runtime_error("Missing CSV header: " + path);
  for (size_t i = 0; i < table.header.size(); i++) {
    if (table.header[i].empty())
      throw std::runtime_error("Empty CSV column name: " + path);
    for (size_t j = 0; j < i; j++)
      if (table.header[i] == table.header[j])
        throw std::runtime_error("Duplicate CSV column: " + table.header[i]);
  }
  if (table.header.size() < prefix.size())
    throw std::runtime_error("Missing numeric CSV columns: " + path);
  for (size_t i = 0; i < prefix.size(); i++)
    if (table.header[i] != prefix[i])
      throw std::runtime_error("Expected CSV column " + prefix[i] + " in " + path);
  Strings row;
  while (csv_record(f, row)) {
    if (row.size() == 1 && row[0].empty())
      continue;
    if (row.size() != table.header.size())
      throw std::runtime_error("Wrong CSV row width: " + path);
    table.rows.push_back(row);
  }
  return table;
}

double csv_double(const std::string &value) {
  size_t used = 0;
  double x = std::stod(value, &used);
  if (used != value.size() || !std::isfinite(x))
    throw std::runtime_error("Invalid finite CSV number: " + value);
  return x;
}
int csv_int(const std::string &value) {
  double x = csv_double(value);
  if (x != std::floor(x) || x < std::numeric_limits<int>::min() ||
      x > std::numeric_limits<int>::max())
    throw std::runtime_error("Invalid CSV integer: " + value);
  return int(x);
}
Metadata csv_metadata(const CsvTable &table, const Strings &row, size_t start) {
  Metadata result;
  for (size_t i = start; i < table.header.size(); i++)
    result.push_back({table.header[i], row[i]});
  return result;
}
std::string csv_quote(const std::string &value) {
  if (value.find_first_of(",\"\r\n") == std::string::npos)
    return value;
  std::string result = "\"";
  for (char c : value) {
    result += c;
    if (c == '"')
      result += c;
  }
  return result + '"';
}
void csv_metadata_header(std::ostream &out, const Metadata &metadata,
                         const std::string &prefix = "") {
  for (const auto &item : metadata)
    out << ',' << csv_quote(prefix + item.first);
}
void csv_metadata_values(std::ostream &out, const Metadata &metadata) {
  for (const auto &item : metadata)
    out << ',' << csv_quote(item.second);
}
const std::string *metadata_value(const Metadata &metadata,
                                  const std::string &key) {
  for (const auto &item : metadata)
    if (item.first == key)
      return &item.second;
  return nullptr;
}
const std::string &required_metadata(const Metadata &metadata,
                                     const std::string &key,
                                     bool allow_empty = false) {
  const auto *value = metadata_value(metadata, key);
  if (!value || (!allow_empty && value->empty()))
    throw std::runtime_error("Missing authoritative metadata: " + key);
  return *value;
}
