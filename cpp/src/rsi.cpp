#include "alphaedge/rsi.hpp"

#include <cmath>

namespace alphaedge {

std::vector<double> compute_rsi(const std::vector<double>& closes, int period) {
    std::vector<double> out(closes.size(), 50.0);
    if (closes.size() < static_cast<size_t>(period + 1)) return out;
    double gain = 0.0, loss = 0.0;
    for (int i = 1; i <= period; ++i) {
        const double d = closes[i] - closes[i - 1];
        if (d >= 0) gain += d; else loss -= d;
    }
    gain /= period; loss /= period;
    for (size_t i = period + 1; i < closes.size(); ++i) {
        const double d = closes[i] - closes[i - 1];
        const double g = d > 0 ? d : 0.0;
        const double l = d < 0 ? -d : 0.0;
        gain = (gain * (period - 1) + g) / period;
        loss = (loss * (period - 1) + l) / period;
        const double rs = loss == 0.0 ? 100.0 : gain / loss;
        out[i] = 100.0 - (100.0 / (1.0 + rs));
    }
    return out;
}

}  // namespace alphaedge
