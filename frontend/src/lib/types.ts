// API types mirroring backend Pydantic schemas. Decimals arrive as JSON strings.

export interface Envelope<T> {
  data: T
  meta: { request_id: string }
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    details: unknown
    request_id: string
  }
}

export interface Paginated<T> {
  items: T[]
  total_count: number
}

// -- Auth ---------------------------------------------------------------

export interface User {
  id: string
  email: string
  display_name: string
  roles: string[]
  is_active: boolean
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

// -- Market data --------------------------------------------------------

export interface Instrument {
  id: string
  symbol: string
  exchange: string
  asset_class: string
  currency: string
  name: string
  is_active: boolean
}

export interface Bar {
  instrument_id: string
  timeframe: string
  timestamp: string
  open: string
  high: string
  low: string
  close: string
  volume: string
  vwap: string | null
  source: string
}

// -- Strategy -----------------------------------------------------------

export interface Strategy {
  id: string
  user_id: string
  name: string
  description: string | null
  strategy_type: 'python' | 'dsl'
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface StrategyVersion {
  id: string
  strategy_id: string
  version: number
  source_code: string
  parameters: Record<string, unknown>
  compiled_hash: string | null
  status: 'draft' | 'validated' | 'published'
  created_at: string
}

export interface ValidationResult {
  version_id: string
  status: string
  compiled_hash: string
  errors: string[]
}

export interface Indicator {
  id: string
  name: string
  category: string
  parameters_schema: Record<string, unknown>
  implementation: string
}

// -- Backtesting ----------------------------------------------------------

export type BacktestStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface BacktestConfig {
  instrument_ids: string[]
  timeframe?: string
  start_date: string
  end_date: string
  initial_capital?: string
  slippage?: { model: 'fixed' | 'percentage'; value: number | string }
  commission?: { per_trade: number | string }
  position_sizing?: { model: 'fixed_quantity' | 'percent_equity'; value: number | string }
  partial_fill_ratio?: number | string
}

export interface BacktestRun {
  id: string
  user_id: string
  strategy_version_id: string
  name: string
  status: BacktestStatus
  config: BacktestConfig
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  celery_task_id: string | null
  created_at: string
  updated_at: string
}

export interface BacktestResult {
  id: string
  backtest_run_id: string
  total_return: string
  annualized_return: string | null
  sharpe_ratio: string | null
  sortino_ratio: string | null
  max_drawdown: string
  win_rate: string | null
  total_trades: number
  profit_factor: string | null
  metrics: Record<string, unknown>
}

export interface BacktestTrade {
  id: string
  instrument_id: string
  side: 'buy' | 'sell'
  quantity: string
  entry_price: string
  exit_price: string | null
  entry_time: string
  exit_time: string | null
  pnl: string | null
  commission: string
  slippage: string
}

export interface EquityPoint {
  timestamp: string
  equity: string
}

// -- Optimization ---------------------------------------------------------

export type OptimizationStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface OptimizationRun {
  id: string
  user_id: string
  strategy_version_id: string
  name: string
  method: 'grid_search' | 'walk_forward'
  objective: string
  parameter_space: Record<string, unknown[]>
  backtest_config: BacktestConfig
  walk_forward_config: Record<string, number> | null
  status: OptimizationStatus
  best_trial_id: string | null
  total_trials: number
  completed_trials: number
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  celery_task_id: string | null
  created_at: string
  updated_at: string
}

export interface OptimizationTrial {
  id: string
  optimization_run_id: string
  backtest_run_id: string | null
  parameters: Record<string, unknown>
  objective_value: string | null
  in_sample_objective: string | null
  window_index: number | null
  rank: number | null
  status: 'pending' | 'running' | 'completed' | 'failed'
  created_at: string
}

// -- Portfolio & risk -------------------------------------------------------

export interface Portfolio {
  id: string
  user_id: string
  name: string
  base_currency: string
  initial_capital: string
  cash_balance: string
  is_paper: boolean
  created_at: string
  updated_at: string
}

export interface Holding {
  id: string
  portfolio_id: string
  instrument_id: string
  quantity: string
  avg_cost: string
  current_price: string
  market_value: string
  updated_at: string
}

export interface PortfolioPerformance {
  total_value: string
  cash_balance: string
  invested_value: string
  initial_capital: string
  total_return: string
  holdings_count: number
}

export interface RiskSnapshot {
  id: string
  portfolio_id: string
  snapshot_at: string
  var_95: string | null
  var_99: string | null
  max_drawdown: string | null
  sharpe_ratio: string | null
  sortino_ratio: string | null
  beta: string | null
  alpha: string | null
  volatility: string | null
  correlation_matrix: Record<string, number> | null
  metrics: Record<string, unknown>
  violations: RiskViolation[]
}

export interface RiskViolation {
  limit_type: string
  threshold: string
  actual: string
  message: string
  instrument_id?: string
}

export interface RiskLimit {
  id: string
  portfolio_id: string
  limit_type: string
  threshold: string
  is_active: boolean
}

// -- Execution ---------------------------------------------------------------

export type OrderStatus =
  | 'pending'
  | 'submitted'
  | 'partially_filled'
  | 'filled'
  | 'cancelled'
  | 'rejected'

export interface BrokerConnection {
  id: string
  user_id: string
  broker_name: string
  is_paper: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Order {
  id: string
  portfolio_id: string
  broker_connection_id: string
  instrument_id: string
  side: 'buy' | 'sell'
  order_type: 'market' | 'limit' | 'stop'
  quantity: string
  filled_quantity: string
  limit_price: string | null
  stop_price: string | null
  status: OrderStatus
  broker_order_id: string | null
  idempotency_key: string | null
  retry_count: number
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface Execution {
  id: string
  order_id: string
  quantity: string
  price: string
  commission: string
  executed_at: string
}

// -- Insights -----------------------------------------------------------------

export type InsightStatus = 'queued' | 'running' | 'completed' | 'failed'

export type InsightType =
  | 'strategy_explanation'
  | 'performance_report'
  | 'risk_interpretation'
  | 'trade_summary'

export interface InsightRequest {
  id: string
  user_id: string
  insight_type: InsightType
  source_type: string
  source_id: string
  status: InsightStatus
  error_message: string | null
  celery_task_id: string | null
  created_at: string
  updated_at: string
}

export interface InsightReport {
  id: string
  insight_request_id: string
  content: string
  metadata: Record<string, unknown>
  created_at: string
}

export interface InsightDetail {
  request: InsightRequest
  report: InsightReport | null
}

// -- Organizations & marketplace ----------------------------------------

export interface Organization {
  id: string
  name: string
  slug: string
  owner_id: string
  plan_tier: string
  created_at: string
}

export interface StrategyListing {
  id: string
  strategy_id: string
  organization_id: string
  title: string
  description: string | null
  price_cents: number
  clone_count: number
  created_at: string
}

export interface CheckoutSession {
  session_id: string
  checkout_url: string
  already_purchased: boolean
  mock: boolean
}

export interface CollabSessionInfo {
  session_id: string
  strategy_id: string
}

export interface LiveTradingStatus {
  live_trading_enabled: boolean
  stripe_configured: boolean
  alpaca_configured: boolean
}
