import { useQuery } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { Stack } from 'expo-router/stack';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  View,
} from 'react-native';

import { api } from '@/api/client';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { bundleIsDownloaded, downloadBundle } from '@/offline/bundles';
import { useAuth } from '@/auth/store';

export default function WorksheetScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const worksheetId = Number(id);
  const { isStudent } = useAuth();

  const { data: bundle, isLoading } = useQuery({
    queryKey: ['worksheet', worksheetId],
    queryFn: () => api.worksheetBundle(worksheetId),
  });

  const [downloaded, setDownloaded] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    bundleIsDownloaded(worksheetId).then(setDownloaded).catch(() => {});
  }, [worksheetId]);

  const download = async () => {
    setDownloading(true);
    setError(null);
    try {
      await downloadBundle(worksheetId);
      setDownloaded(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  const start = async () => {
    setStarting(true);
    setError(null);
    try {
      const attempt = await api.startAttempt(worksheetId);
      const firstPage = bundle?.pages[0];
      router.push(
        `/(app)/write?attempt=${attempt.id}&page=${firstPage?.id ?? ''}` as never,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start attempt');
    } finally {
      setStarting(false);
    }
  };

  if (isLoading || !bundle) {
    return (
      <ThemedView style={styles.center}>
        <ActivityIndicator size="large" />
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      <Stack.Screen options={{ title: bundle.title }} />
      <ThemedText type="title" style={styles.title}>
        {bundle.title}
      </ThemedText>
      <ThemedText type="small">
        {bundle.subject_name}
        {bundle.exam_year ? ` · ${bundle.exam_year}` : ''}
        {bundle.source ? ` · ${bundle.source}` : ''}
      </ThemedText>
      {!!bundle.description && (
        <ThemedText type="small">{bundle.description}</ThemedText>
      )}
      <ThemedText type="small">
        {bundle.pages.length} page{bundle.pages.length === 1 ? '' : 's'}
      </ThemedText>

      {error && (
        <ThemedText type="small" style={styles.error}>
          {error}
        </ThemedText>
      )}

      <View style={styles.actions}>
        <Pressable
          style={[styles.button, downloading && styles.disabled]}
          onPress={download}
          disabled={downloading}
        >
          {downloading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <ThemedText style={styles.buttonText}>
              {downloaded ? 'Downloaded ✓' : 'Download for offline'}
            </ThemedText>
          )}
        </Pressable>

        {isStudent && (
          <Pressable
            style={[styles.button, styles.primary, starting && styles.disabled]}
            onPress={start}
            disabled={starting}
          >
            {starting ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <ThemedText style={styles.buttonText}>Start writing</ThemedText>
            )}
          </Pressable>
        )}
      </View>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: Spacing.three, gap: Spacing.two },
  center: { flex: 1, justifyContent: 'center' },
  title: { fontSize: 28 },
  error: { color: '#c00' },
  actions: { gap: Spacing.two, marginTop: Spacing.four },
  button: {
    backgroundColor: '#9aa0aa',
    borderRadius: 10,
    padding: Spacing.three,
    alignItems: 'center',
  },
  primary: { backgroundColor: '#208AEF' },
  disabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
