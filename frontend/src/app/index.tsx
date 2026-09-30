import { Redirect } from 'expo-router';
import { useEffect } from 'react';
import * as SplashScreen from 'expo-splash-screen';

import { useAuth } from '@/auth/store';

export default function Index() {
  const { user, loading } = useAuth();

  useEffect(() => {
    if (!loading) SplashScreen.hideAsync();
  }, [loading]);

  if (loading) return null;
  return <Redirect href={user ? '/(app)' : '/login'} />;
}
