// Size/capacity probe only; mirrors Datum's fields in src/main.cpp.
#include "../../../src/csv.hpp"
#include <iostream>
struct Datum { int i,j,k,type; double value; Metadata metadata; double weight; int station_j; };
struct Entry { int col; double val; };
int main() {
  Metadata metadata;
  for (int i=0; i<18; ++i) metadata.push_back({"key", "value"});
  std::cout << "{\"string\":" << sizeof(std::string)
    << ",\"metadata_pair\":" << sizeof(Metadata::value_type)
    << ",\"metadata_capacity\":" << metadata.capacity()
    << ",\"datum\":" << sizeof(Datum)
    << ",\"vector\":" << sizeof(Strings)
    << ",\"entry\":" << sizeof(Entry) << "}\n";
}
