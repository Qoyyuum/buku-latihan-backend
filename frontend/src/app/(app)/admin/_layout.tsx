import { Redirect } from 'expo-router';
import { Stack } from 'expo-router/stack';

import { useAuth } from '@/auth/store';

export default function AdminLayout() {
  const { isTeacher } = useAuth();
  if (!isTeacher) return <Redirect href="/(app)" />;
  return <Stack screenOptions={{ headerShown: true }} />;
}
