import { NavigationContainer, DarkTheme } from '@react-navigation/native'
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StatusBar } from 'expo-status-bar'
import { useEffect, useState } from 'react'
import { Text } from 'react-native'
import { loadTokens, saveTokens } from './src/api'
import HomeScreen from './src/screens/HomeScreen'
import LoginScreen from './src/screens/LoginScreen'
import OrdersScreen from './src/screens/OrdersScreen'

const Tab = createBottomTabNavigator()
const qc = new QueryClient()

const theme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: '#0a0e14',
    card: '#111827',
    primary: '#c8ff00',
    text: '#f3f4f6',
    border: '#374151',
  },
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: '#111827' },
        headerTintColor: '#c8ff00',
        tabBarStyle: { backgroundColor: '#111827', borderTopColor: '#374151' },
        tabBarActiveTintColor: '#c8ff00',
        tabBarInactiveTintColor: '#6b7280',
      }}
    >
      <Tab.Screen name="Overview" component={HomeScreen} />
      <Tab.Screen name="Orders" component={OrdersScreen} />
    </Tab.Navigator>
  )
}

export default function App() {
  const [ready, setReady] = useState(false)
  const [loggedIn, setLoggedIn] = useState(false)

  useEffect(() => {
    void (async () => {
      const tokens = await loadTokens()
      setLoggedIn(!!tokens?.access_token)
      setReady(true)
    })()
  }, [])

  if (!ready) {
    return <Text style={{ color: '#c8ff00', marginTop: 80, textAlign: 'center' }}>Loading…</Text>
  }

  return (
    <QueryClientProvider client={qc}>
      <NavigationContainer theme={theme}>
        {loggedIn ? (
          <MainTabs />
        ) : (
          <LoginScreen
            onLoggedIn={() => setLoggedIn(true)}
          />
        )}
        <StatusBar style="light" />
      </NavigationContainer>
    </QueryClientProvider>
  )
}

export async function logout(): Promise<void> {
  await saveTokens(null)
}
