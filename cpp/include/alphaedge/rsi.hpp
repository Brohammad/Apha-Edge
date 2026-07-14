#pragma once

#include <vector>

namespace alphaedge {

std::vector<double> compute_rsi(const std::vector<double>& closes, int period);

}  // namespace alphaedge
