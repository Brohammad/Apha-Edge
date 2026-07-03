import { useQuery } from '@tanstack/react-query'
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native'
import { api } from '../api'

interface Order {
  id: string
  side: string
  order_type: string
  quantity: string
  status: string
}

export default function OrdersScreen() {
  const { data, isLoading } = useQuery({
    queryKey: ['orders'],
    queryFn: () => api<{ items: Order[] }>('/orders'),
  })

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color="#c8ff00" />
      </View>
    )
  }

  const items = data?.items ?? []

  return (
    <View style={styles.root}>
      <FlatList
        data={items}
        keyExtractor={(o) => o.id}
        contentContainerStyle={styles.list}
        ListEmptyComponent={<Text style={styles.empty}>No orders yet</Text>}
        renderItem={({ item }) => (
          <View style={styles.row}>
            <Text style={[styles.side, item.side === 'buy' ? styles.buy : styles.sell]}>
              {item.side.toUpperCase()}
            </Text>
            <Text style={styles.meta}>
              {item.order_type} · {item.quantity} · {item.status}
            </Text>
          </View>
        )}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0a0e14' },
  center: { flex: 1, backgroundColor: '#0a0e14', justifyContent: 'center', alignItems: 'center' },
  list: { padding: 16, gap: 8 },
  empty: { color: '#6b7280', textAlign: 'center', marginTop: 40 },
  row: {
    backgroundColor: '#111827',
    borderRadius: 10,
    borderColor: '#374151',
    borderWidth: 1,
    padding: 14,
    marginBottom: 8,
  },
  side: { fontWeight: '800', fontSize: 14, fontFamily: 'monospace' },
  buy: { color: '#4ade80' },
  sell: { color: '#f87171' },
  meta: { color: '#9ca3af', fontSize: 12, marginTop: 4, fontFamily: 'monospace' },
})
