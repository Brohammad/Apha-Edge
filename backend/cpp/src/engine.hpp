#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <stdexcept>
#include <vector>

#include "indicators.hpp"

namespace alphaedge {

// Enums use the same ordinals the Python bridge encodes:
// slippage: 0=fixed 1=percentage | sizing: 0=fixed_quantity 1=percent_equity
// rule fn: 0=crossover 1=crossunder | action: 0=BUY 1=SELL 2=HOLD
struct EngineConfig {
    double initial_capital;
    int slippage_model;
    double slippage_value;
    double commission_per_trade;
    int sizing_model;
    double sizing_value;
    double partial_fill_ratio;
};

struct Rule {
    int left;    // index into indicator specs
    int right;   // index into indicator specs
    int fn;
    int action;
};

struct TradeRecord {
    int32_t instrument;
    double quantity;
    double entry_price;
    double exit_price;
    int64_t entry_ts;
    int64_t exit_ts;
    double pnl;
    double commission;
    double slippage;
    bool closed;
};

struct Metrics {
    double total_return = 0.0;
    double annualized_return = kNaN;
    double sharpe = kNaN;
    double sortino = kNaN;
    double max_drawdown = 0.0;
    double win_rate = kNaN;
    double profit_factor = kNaN;
    double final_equity = 0.0;
    int64_t days = 0;
};

struct EngineResult {
    std::vector<int64_t> equity_ts;
    std::vector<double> equity;
    std::vector<TradeRecord> trades;  // closed trades only, in close order
    Metrics metrics;
};

// Python Decimal.quantize(Decimal("0.0001")) defaults to ROUND_HALF_EVEN;
// nearbyint under the default FE_TONEAREST mode rounds ties to even.
inline double quantize4(double v) { return std::nearbyint(v * 10000.0) / 10000.0; }

struct Fill {
    double quantity;
    double price;
    double commission;
    double slippage;
    bool ok;
};

inline Fill simulate_fill(bool is_buy, double requested_qty, double price,
                          const EngineConfig& cfg) {
    if (requested_qty <= 0.0) return {0, 0, 0, 0, false};
    const double filled = quantize4(requested_qty * cfg.partial_fill_ratio);
    if (filled <= 0.0) return {0, 0, 0, 0, false};
    const double adj =
        cfg.slippage_model == 0 ? cfg.slippage_value : price * cfg.slippage_value;
    const double fill_price = is_buy ? price + adj : price - adj;
    return {filled, fill_price, cfg.commission_per_trade, adj, true};
}

inline double compute_buy_quantity(double price, double equity, double cash,
                                   const EngineConfig& cfg) {
    double qty;
    if (cfg.sizing_model == 0) {
        qty = cfg.sizing_value;
    } else {
        qty = price > 0.0 ? quantize4(equity * cfg.sizing_value / price) : 0.0;
    }
    const double max_affordable = price > 0.0 ? quantize4(cash / price) : 0.0;
    return std::min(qty, max_affordable);
}

namespace detail {

struct IndicatorState {
    std::vector<AnyIndicator> indicators;
    std::vector<double> prev;
    std::vector<double> current;

    explicit IndicatorState(const std::vector<IndicatorSpec>& specs) {
        indicators.reserve(specs.size());
        for (const auto& s : specs) indicators.emplace_back(s);
        prev.assign(specs.size(), kNaN);
        current.assign(specs.size(), kNaN);
    }

    void update(double close) {
        for (size_t i = 0; i < indicators.size(); ++i) {
            prev[i] = current[i];
            current[i] = indicators[i].update(close);
        }
    }
};

inline bool crossed(int fn, double pl, double pr, double cl, double cr) {
    if (std::isnan(pl) || std::isnan(pr)) return false;
    return fn == 0 ? (pl <= pr && cl > cr) : (pl >= pr && cl < cr);
}

inline void compute_metrics(const EngineConfig& cfg, EngineResult& out) {
    Metrics& m = out.metrics;
    const auto& eq = out.equity;
    const auto& ts = out.equity_ts;

    // Trade stats over closed trades with pnl.
    int wins = 0, losses = 0, closed = 0;
    double gross_profit = 0.0, gross_loss = 0.0;
    for (const auto& t : out.trades) {
        if (!t.closed) continue;
        ++closed;
        if (t.pnl > 0.0) { ++wins; gross_profit += t.pnl; }
        else if (t.pnl < 0.0) { ++losses; gross_loss += -t.pnl; }
    }
    if (closed > 0) {
        m.win_rate = static_cast<double>(wins) / closed;
        if (gross_loss > 0.0) m.profit_factor = gross_profit / gross_loss;
    }

    if (eq.empty()) {
        m.final_equity = cfg.initial_capital;
        return;
    }

    m.final_equity = eq.back();
    m.total_return = (m.final_equity - cfg.initial_capital) / cfg.initial_capital;

    // Python: days = max((last - first).days, 1); timedelta.days floors.
    const int64_t span_us = ts.back() - ts.front();
    m.days = std::max<int64_t>(span_us / 86'400'000'000LL, 1);
    if (m.final_equity > 0.0 && cfg.initial_capital > 0.0) {
        // Mirrors the Python formula: ratio ** (365/days - 1).
        const double exponent = 365.0 / static_cast<double>(m.days) - 1.0;
        m.annualized_return = std::pow(m.final_equity / cfg.initial_capital, exponent);
    }

    std::vector<double> returns;
    returns.reserve(eq.size());
    for (size_t i = 1; i < eq.size(); ++i) {
        if (eq[i - 1] > 0.0) returns.push_back((eq[i] - eq[i - 1]) / eq[i - 1]);
    }
    if (returns.size() >= 2) {
        const double n = static_cast<double>(returns.size());
        const double mean = std::accumulate(returns.begin(), returns.end(), 0.0) / n;
        double var = 0.0, downside = 0.0;
        for (double r : returns) {
            var += (r - mean) * (r - mean);
            const double d = std::min(0.0, r);
            downside += d * d;
        }
        const double std_dev = std::sqrt(var / (n - 1.0));
        if (std_dev > 0.0) m.sharpe = mean / std_dev * std::sqrt(252.0);
        const double downside_dev = std::sqrt(downside / n);
        if (downside_dev > 0.0) m.sortino = mean / downside_dev * std::sqrt(252.0);
    }

    double peak = eq.front();
    double max_dd = 0.0;
    for (double v : eq) {
        if (v > peak) peak = v;
        if (peak > 0.0) max_dd = std::max(max_dd, (peak - v) / peak);
    }
    m.max_drawdown = max_dd;
}

}  // namespace detail

// bars: parallel arrays (instrument index, epoch-microsecond timestamp, close).
// Bars are stable-sorted by timestamp, preserving input order for ties,
// matching Python's list.sort on merged per-instrument lists.
inline EngineResult run_backtest(const std::vector<IndicatorSpec>& specs,
                                 const std::vector<Rule>& rules,
                                 const std::vector<int32_t>& instrument,
                                 const std::vector<int64_t>& timestamp,
                                 const std::vector<double>& close,
                                 int n_instruments,
                                 const EngineConfig& cfg) {
    const size_t n = close.size();
    if (instrument.size() != n || timestamp.size() != n) {
        throw std::invalid_argument("bar arrays must have equal length");
    }
    for (const auto& r : rules) {
        const int max_idx = static_cast<int>(specs.size());
        if (r.left < 0 || r.left >= max_idx || r.right < 0 || r.right >= max_idx) {
            throw std::invalid_argument("rule references unknown indicator spec");
        }
    }

    std::vector<size_t> order(n);
    std::iota(order.begin(), order.end(), 0);
    std::stable_sort(order.begin(), order.end(), [&](size_t a, size_t b) {
        return timestamp[a] < timestamp[b];
    });

    std::vector<detail::IndicatorState> states;
    states.reserve(static_cast<size_t>(n_instruments));
    for (int i = 0; i < n_instruments; ++i) states.emplace_back(specs);

    EngineResult out;
    out.equity_ts.reserve(n);
    out.equity.reserve(n);

    double cash = cfg.initial_capital;
    std::vector<double> positions(static_cast<size_t>(n_instruments), 0.0);
    std::vector<double> last_price(static_cast<size_t>(n_instruments), kNaN);
    // Index of the open trade per instrument in out.trades, -1 if none.
    std::vector<int64_t> open_trade(static_cast<size_t>(n_instruments), -1);
    double last_equity = cash;
    bool has_equity = false;

    auto close_position = [&](int32_t iid, double price, int64_t ts) {
        const double pos = positions[static_cast<size_t>(iid)];
        if (pos <= 0.0) return;
        const Fill fill = simulate_fill(false, pos, price, cfg);
        if (!fill.ok) return;
        cash += fill.price * fill.quantity - fill.commission;
        positions[static_cast<size_t>(iid)] = 0.0;
        const int64_t ti = open_trade[static_cast<size_t>(iid)];
        if (ti >= 0) {
            TradeRecord& t = out.trades[static_cast<size_t>(ti)];
            t.exit_price = fill.price;
            t.exit_ts = ts;
            t.commission += fill.commission;
            t.slippage += fill.slippage;
            t.pnl = (fill.price - t.entry_price) * t.quantity - t.commission;
            t.closed = true;
            open_trade[static_cast<size_t>(iid)] = -1;
        }
    };

    for (size_t k = 0; k < n; ++k) {
        const size_t i = order[k];
        const int32_t iid = instrument[i];
        const double px = close[i];
        const int64_t ts = timestamp[i];
        last_price[static_cast<size_t>(iid)] = px;

        detail::IndicatorState& state = states[static_cast<size_t>(iid)];
        state.update(px);

        int action = -1;
        for (const auto& rule : rules) {
            const double cl = state.current[static_cast<size_t>(rule.left)];
            const double cr = state.current[static_cast<size_t>(rule.right)];
            if (std::isnan(cl) || std::isnan(cr)) continue;
            const double pl = state.prev[static_cast<size_t>(rule.left)];
            const double pr = state.prev[static_cast<size_t>(rule.right)];
            if (detail::crossed(rule.fn, pl, pr, cl, cr)) {
                action = rule.action;
                break;
            }
        }

        if (action == 0) {  // BUY
            const double pos = positions[static_cast<size_t>(iid)];
            if (pos <= 0.0) {
                const double equity = has_equity ? last_equity : cash;
                const double qty = compute_buy_quantity(px, equity, cash, cfg);
                const Fill fill = simulate_fill(true, qty, px, cfg);
                if (fill.ok) {
                    const double cost = fill.price * fill.quantity + fill.commission;
                    if (cost <= cash) {
                        cash -= cost;
                        positions[static_cast<size_t>(iid)] = pos + fill.quantity;
                        open_trade[static_cast<size_t>(iid)] =
                            static_cast<int64_t>(out.trades.size());
                        out.trades.push_back({iid, fill.quantity, fill.price, kNaN, ts, 0,
                                              kNaN, fill.commission, fill.slippage, false});
                    }
                }
            }
        } else if (action == 1) {  // SELL
            close_position(iid, px, ts);
        }
        // HOLD and no-signal: no trade.

        double holdings = 0.0;
        for (int j = 0; j < n_instruments; ++j) {
            const double q = positions[static_cast<size_t>(j)];
            if (q != 0.0 && !std::isnan(last_price[static_cast<size_t>(j)])) {
                holdings += q * last_price[static_cast<size_t>(j)];
            }
        }
        last_equity = cash + holdings;
        has_equity = true;
        out.equity_ts.push_back(ts);
        out.equity.push_back(last_equity);
    }

    // Force-close remaining positions at their last seen price.
    if (n > 0) {
        const int64_t final_ts = timestamp[order.back()];
        for (int j = 0; j < n_instruments; ++j) {
            if (open_trade[static_cast<size_t>(j)] >= 0) {
                const size_t ti = static_cast<size_t>(open_trade[static_cast<size_t>(j)]);
                const double px = std::isnan(last_price[static_cast<size_t>(j)])
                                      ? out.trades[ti].entry_price
                                      : last_price[static_cast<size_t>(j)];
                close_position(static_cast<int32_t>(j), px, final_ts);
            }
        }
    }

    // Drop trades that never closed (mirrors Python: open trades whose
    // force-close fill failed are excluded from the closed list).
    std::vector<TradeRecord> closed;
    closed.reserve(out.trades.size());
    for (const auto& t : out.trades) {
        if (t.closed) closed.push_back(t);
    }
    out.trades = std::move(closed);

    detail::compute_metrics(cfg, out);
    return out;
}

}  // namespace alphaedge
