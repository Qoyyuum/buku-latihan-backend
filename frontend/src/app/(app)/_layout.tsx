import { Redirect } from 'expo-router';
import { Stack } from 'expo-router/stack';
import { ActivityIndicator, View } from 'react-native';

import { useAuth } from '@/auth/store';

export default function AppLayout() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center' }}>
        <ActivityIndicator size="large" />
      </View>
    );
  }
  if (!user) return <Redirect href="/login" />;

  return <Stack screenOptions={{ headerShown: true }} />;
}
