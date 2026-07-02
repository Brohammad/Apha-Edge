#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "engine.hpp"

namespace py = pybind11;

using alphaedge::EngineConfig;
using alphaedge::EngineResult;
using alphaedge::IndicatorSpec;
using alphaedge::Rule;

namespace {

py::dict result_to_dict(const EngineResult& res) {
    py::list trades;
    for (const auto& t : res.trades) {
        py::dict d;
        d["instrument"] = t.instrument;
        d["quantity"] = t.quantity;
        d["entry_price"] = t.entry_price;
        d["exit_price"] = t.exit_price;
        d["entry_ts"] = t.entry_ts;
        d["exit_ts"] = t.exit_ts;
        d["pnl"] = t.pnl;
        d["commission"] = t.commission;
        d["slippage"] = t.slippage;
        trades.append(d);
    }

    py::dict metrics;
    metrics["total_return"] = res.metrics.total_return;
    metrics["annualized_return"] = res.metrics.annualized_return;
    metrics["sharpe"] = res.metrics.sharpe;
    metrics["sortino"] = res.metrics.sortino;
    metrics["max_drawdown"] = res.metrics.max_drawdown;
    metrics["win_rate"] = res.metrics.win_rate;
    metrics["profit_factor"] = res.metrics.profit_factor;
    metrics["final_equity"] = res.metrics.final_equity;
    metrics["days"] = res.metrics.days;

    py::dict out;
    out["equity_ts"] = py::cast(res.equity_ts);
    out["equity"] = py::cast(res.equity);
    out["trades"] = trades;
    out["metrics"] = metrics;
    return out;
}

}  // namespace

PYBIND11_MODULE(alphaedge_cpp, m) {
    m.doc() = "AlphaEdge C++ backtest acceleration (Phase 4b)";
    m.attr("__version__") = "0.1.0";

    m.def(
        "run_backtest",
        [](const std::vector<std::tuple<int, int, int, int, double>>& specs,
           const std::vector<std::tuple<int, int, int, int>>& rules,
           const std::vector<int32_t>& instrument,
           const std::vector<int64_t>& timestamp,
           const std::vector<double>& close,
           int n_instruments,
           double initial_capital,
           int slippage_model,
           double slippage_value,
           double commission_per_trade,
           int sizing_model,
           double sizing_value,
           double partial_fill_ratio) {
            std::vector<IndicatorSpec> spec_vec;
            spec_vec.reserve(specs.size());
            for (const auto& [kind, p1, p2, p3, std_dev] : specs) {
                spec_vec.push_back({kind, p1, p2, p3, std_dev});
            }
            std::vector<Rule> rule_vec;
            rule_vec.reserve(rules.size());
            for (const auto& [left, right, fn, action] : rules) {
                rule_vec.push_back({left, right, fn, action});
            }
            EngineConfig cfg{initial_capital, slippage_model,   slippage_value,
                             commission_per_trade, sizing_model, sizing_value,
                             partial_fill_ratio};

            EngineResult res;
            {
                py::gil_scoped_release release;
                res = alphaedge::run_backtest(spec_vec, rule_vec, instrument, timestamp,
                                              close, n_instruments, cfg);
            }
            return result_to_dict(res);
        },
        py::arg("specs"), py::arg("rules"), py::arg("instrument"), py::arg("timestamp"),
        py::arg("close"), py::arg("n_instruments"), py::arg("initial_capital"),
        py::arg("slippage_model"), py::arg("slippage_value"),
        py::arg("commission_per_trade"), py::arg("sizing_model"), py::arg("sizing_value"),
        py::arg("partial_fill_ratio"),
        "Run a DSL backtest over pre-sorted bar arrays; returns equity curve, "
        "closed trades, and metrics.");
}
