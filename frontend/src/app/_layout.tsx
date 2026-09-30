import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router/stack';
import * as SplashScreen from 'expo-splash-screen';
import { useColorScheme } from 'react-native';
import {
  DarkTheme,
  DefaultTheme,
  ThemeProvider,
} from 'expo-router/react-navigation';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import { AuthProvider } from '@/auth/store';

SplashScreen.preventAutoHideAsync();

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});

export default function RootLayout() {
  const colorScheme = useColorScheme();
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ThemeProvider
            value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}
          >
            <Stack screenOptions={{ headerShown: true }}>
              <Stack.Screen name="login" options={{ headerShown: false }} />
              <Stack.Screen name="(app)" options={{ headerShown: false }} />
            </Stack>
          </ThemeProvider>
        </AuthProvider>
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}
