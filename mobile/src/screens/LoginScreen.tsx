import { useState } from 'react'
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import { api, saveTokens, type TokenPair } from '../api'

interface Props {
  onLoggedIn: () => void
}

export default function LoginScreen({ onLoggedIn }: Props) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    setLoading(true)
    setError(null)
    try {
      const tokens = await api<TokenPair>('/auth/login', {
        method: 'POST',
        body: { email, password },
        auth: false,
      })
      if (!tokens.refresh_token) {
        throw new Error('Login response missing refresh token')
      }
      await saveTokens(tokens as TokenPair)
      onLoggedIn()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.card}>
        <Text style={styles.logo}>AlphaEdge</Text>
        <Text style={styles.sub}>Mobile terminal</Text>
        {error && <Text style={styles.error}>{error}</Text>}
        <TextInput
          style={styles.input}
          placeholder="Email"
          placeholderTextColor="#6b7280"
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
        />
        <TextInput
          style={styles.input}
          placeholder="Password"
          placeholderTextColor="#6b7280"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />
        <Pressable style={styles.btn} onPress={() => void submit()} disabled={loading}>
          {loading ? (
            <ActivityIndicator color="#0a0e14" />
          ) : (
            <Text style={styles.btnText}>Sign in</Text>
          )}
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#0a0e14',
    justifyContent: 'center',
    padding: 24,
  },
  card: { gap: 12 },
  logo: { color: '#c8ff00', fontSize: 28, fontWeight: '800' },
  sub: { color: '#9ca3af', fontSize: 13, marginBottom: 8, fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace' },
  input: {
    backgroundColor: '#111827',
    borderColor: '#374151',
    borderWidth: 1,
    borderRadius: 10,
    padding: 14,
    color: '#f3f4f6',
    fontSize: 16,
  },
  btn: {
    backgroundColor: '#c8ff00',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
    marginTop: 8,
  },
  btnText: { color: '#0a0e14', fontWeight: '700', fontSize: 16 },
  error: { color: '#f87171', fontSize: 13 },
})
