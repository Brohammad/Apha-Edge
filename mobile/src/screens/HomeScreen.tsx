import { useQuery } from '@tanstack/react-query'
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native'
import { api } from '../api'

interface Portfolio {
  id: string
  name: string
  cash_balance: string
  is_paper: boolean
}

export default function HomeScreen() {
  const { data, isLoading } = useQuery({
    queryKey: ['portfolios'],
    queryFn: () => api<{ items: Portfolio[]; total_count: number }>('/portfolios'),
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
    <ScrollView style={styles.root} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Overview</Text>
      <Text style={styles.sub}>{items.length} portfolio(s)</Text>
      {items.map((p) => (
        <View key={p.id} style={styles.card}>
          <Text style={styles.cardTitle}>{p.name}</Text>
          <Text style={styles.meta}>
            Cash ${Number(p.cash_balance).toLocaleString()} · {p.is_paper ? 'PAPER' : 'LIVE'}
          </Text>
        </View>
      ))}
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0a0e14' },
  content: { padding: 16, gap: 12 },
  center: { flex: 1, backgroundColor: '#0a0e14', justifyContent: 'center', alignItems: 'center' },
  title: { color: '#f9fafb', fontSize: 22, fontWeight: '700' },
  sub: { color: '#6b7280', fontSize: 13, marginBottom: 8 },
  card: {
    backgroundColor: '#111827',
    borderRadius: 12,
    borderColor: '#374151',
    borderWidth: 1,
    padding: 16,
  },
  cardTitle: { color: '#f3f4f6', fontSize: 16, fontWeight: '600' },
  meta: { color: '#9ca3af', fontSize: 12, marginTop: 4, fontFamily: 'monospace' },
})
