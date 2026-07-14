import { useState } from 'react'
import Modal from './Modal'
import { btnPrimary, inputCls } from './ui'

type BrokerFormProps = {
  brokerName: string
  isPaper: boolean
  onClose: () => void
  onSubmit: (credentials: Record<string, string>) => void
  isPending: boolean
}

export function BrokerConnectionModal({
  brokerName,
  isPaper,
  onClose,
  onSubmit,
  isPending,
}: BrokerFormProps) {
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [accountId, setAccountId] = useState('')

  return (
    <Modal title={`Connect ${brokerName}`} onClose={onClose}>
      <form
        className="mt-3 space-y-3"
        onSubmit={(e) => {
          e.preventDefault()
          if (brokerName === 'alpaca') {
            onSubmit({ api_key: apiKey, api_secret: apiSecret })
          } else if (brokerName === 'ibkr') {
            onSubmit({ account_id: accountId })
          } else {
            onSubmit({})
          }
        }}
      >
        {brokerName === 'alpaca' && (
          <>
            <input
              required
              placeholder="API key"
              className={inputCls}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
            <input
              required
              type="password"
              placeholder="API secret"
              className={inputCls}
              value={apiSecret}
              onChange={(e) => setApiSecret(e.target.value)}
            />
          </>
        )}
        {brokerName === 'ibkr' && (
          <input
            required
            placeholder="IBKR account ID"
            className={inputCls}
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
          />
        )}
        {brokerName === 'paper' && (
          <p className="text-sm text-ink-400">Paper broker requires no credentials.</p>
        )}
        <button type="submit" disabled={isPending} className={`${btnPrimary} w-full`}>
          {isPending ? 'Connecting…' : `Connect ${isPaper ? 'paper' : 'live'}`}
        </button>
      </form>
    </Modal>
  )
}
