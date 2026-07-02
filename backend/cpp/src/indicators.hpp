#pragma once

#include <cmath>
#include <limits>
#include <stdexcept>
#include <variant>
#include <vector>

namespace alphaedge {

inline constexpr double kNaN = std::numeric_limits<double>::quiet_NaN();

// Mirrors alphaedge.modules.strategy.domain.indicators semantics:
// indicators return NaN (Python: None) until enough data has been seen.

struct IndicatorSpec {
    int kind;  // 0=sma 1=ema 2=rsi 3=macd 4=bollinger
    int p1;    // period (sma/ema/rsi/bollinger) or fast_period (macd)
    int p2;    // slow_period (macd)
    int p3;    // signal_period (macd)
    double std_dev;  // bollinger only
};

// Fixed-size circular buffer. Sums in insertion (age) order to match the
// Python deque summation as closely as floating point allows.
class RollingWindow {
public:
    explicit RollingWindow(int period) : period_(period), buf_(static_cast<size_t>(period), 0.0) {
        if (period < 1) throw std::invalid_argument("window period must be >= 1");
    }

    void push(double v) {
        buf_[static_cast<size_t>(head_)] = v;
        head_ = (head_ + 1) % period_;
        if (count_ < period_) ++count_;
    }

    bool full() const { return count_ == period_; }

    double sum() const {
        double s = 0.0;
        const int start = full() ? head_ : 0;
        for (int i = 0; i < count_; ++i) {
            s += buf_[static_cast<size_t>((start + i) % period_)];
        }
        return s;
    }

private:
    int period_;
    std::vector<double> buf_;
    int head_ = 0;
    int count_ = 0;
};

class Sma {
public:
    explicit Sma(int period) : period_(period), window_(period) {}

    double update(double v) {
        window_.push(v);
        if (!window_.full()) return kNaN;
        return window_.sum() / period_;
    }

private:
    int period_;
    RollingWindow window_;
};

class Ema {
public:
    explicit Ema(int period) : period_(period), multiplier_(2.0 / (period + 1.0)) {
        if (period < 1) throw std::invalid_argument("EMA period must be >= 1");
    }

    double update(double v) {
        ++count_;
        if (std::isnan(value_)) {
            value_ = v;
        } else {
            value_ = (v - value_) * multiplier_ + value_;
        }
        return count_ >= period_ ? value_ : kNaN;
    }

private:
    int period_;
    double multiplier_;
    double value_ = kNaN;
    int count_ = 0;
};

class Rsi {
public:
    explicit Rsi(int period) : period_(period), gains_(period), losses_(period) {
        if (period < 2) throw std::invalid_argument("RSI period must be >= 2");
    }

    double update(double v) {
        if (!std::isnan(prev_)) {
            const double change = v - prev_;
            gains_.push(change > 0.0 ? change : 0.0);
            losses_.push(change < 0.0 ? -change : 0.0);
            ++samples_;
        }
        prev_ = v;
        if (samples_ < period_) return kNaN;
        const double avg_gain = gains_.sum() / period_;
        const double avg_loss = losses_.sum() / period_;
        if (avg_loss == 0.0) return 100.0;
        const double rs = avg_gain / avg_loss;
        return 100.0 - (100.0 / (1.0 + rs));
    }

private:
    int period_;
    RollingWindow gains_;
    RollingWindow losses_;
    double prev_ = kNaN;
    int samples_ = 0;
};

// Matches Python MACD.update: emits the *signal line* value (EMA of the MACD
// line), NaN until the signal EMA is ready.
class Macd {
public:
    Macd(int fast_period, int slow_period, int signal_period)
        : fast_(fast_period), slow_(slow_period), signal_(signal_period) {}

    double update(double v) {
        const double fast = fast_.update(v);
        const double slow = slow_.update(v);
        if (std::isnan(fast) || std::isnan(slow)) return kNaN;
        return signal_.update(fast - slow);
    }

private:
    Ema fast_;
    Ema slow_;
    Ema signal_;
};

// Matches Python BollingerBands.update: returns the middle band (SMA).
// Upper/lower bands are not consumed by DSL signal evaluation.
class Bollinger {
public:
    Bollinger(int period, double std_dev) : sma_(period), std_dev_(std_dev) {}

    double update(double v) { return sma_.update(v); }

private:
    Sma sma_;
    double std_dev_;
};

class AnyIndicator {
public:
    explicit AnyIndicator(const IndicatorSpec& spec) : impl_(make(spec)) {}

    double update(double v) {
        return std::visit([v](auto& ind) { return ind.update(v); }, impl_);
    }

private:
    using Variant = std::variant<Sma, Ema, Rsi, Macd, Bollinger>;

    static Variant make(const IndicatorSpec& s) {
        switch (s.kind) {
            case 0: return Sma(s.p1);
            case 1: return Ema(s.p1);
            case 2: return Rsi(s.p1);
            case 3: return Macd(s.p1, s.p2, s.p3);
            case 4: return Bollinger(s.p1, s.std_dev);
            default: throw std::invalid_argument("unknown indicator kind");
        }
    }

    Variant impl_;
};

}  // namespace alphaedge
