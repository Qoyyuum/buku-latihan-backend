import { Redirect } from 'expo-router';

import { useAuth } from '@/auth/store';

export default function Index() {
  const { isTeacher } = useAuth();
  // Teachers land on the dashboard; students/parents on subjects.
  return <Redirect href={isTeacher ? '/(app)/dashboard' : '/(app)/subjects'} />;
}
