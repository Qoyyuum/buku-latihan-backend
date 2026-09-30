import { router } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useAuth } from '@/auth/store';

export default function LoginScreen() {
  const { user, loading, login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    SplashScreen.hideAsync();
  }, []);

  useEffect(() => {
    if (!loading && user) router.replace('/(app)');
  }, [loading, user]);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password);
      router.replace('/(app)');
    } catch {
      setError('Invalid username or password.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safe}>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={styles.form}
        >
          <ThemedText type="title" style={styles.title}>
            Buku Latihan
          </ThemedText>
          <ThemedText type="small" style={styles.subtitle}>
            Practice past-year papers with your pen
          </ThemedText>

          <TextInput
            style={styles.input}
            placeholder="Username"
            autoCapitalize="none"
            value={username}
            onChangeText={setUsername}
            onSubmitEditing={submit}
          />
          <TextInput
            style={styles.input}
            placeholder="Password"
            secureTextEntry
            value={password}
            onChangeText={setPassword}
            onSubmitEditing={submit}
          />

          {error && (
            <ThemedText type="small" style={styles.error}>
              {error}
            </ThemedText>
          )}

          <Pressable style={styles.button} onPress={submit} disabled={busy}>
            {busy ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <ThemedText style={styles.buttonText}>Sign in</ThemedText>
            )}
          </Pressable>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  safe: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  form: { width: '100%', maxWidth: 360, gap: Spacing.three, padding: Spacing.four },
  title: { textAlign: 'center' },
  subtitle: { textAlign: 'center', opacity: 0.7 },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    padding: Spacing.three,
    fontSize: 16,
    backgroundColor: '#fff',
    color: '#000',
  },
  error: { color: '#c00' },
  button: {
    backgroundColor: '#208AEF',
    borderRadius: 8,
    padding: Spacing.three,
    alignItems: 'center',
  },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
