import { useQuery } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { Stack } from 'expo-router/stack';
import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  Pressable,
  StyleSheet,
  View,
} from 'react-native';

import { api } from '@/api/client';
import type { Stroke } from '@/api/types';
import { useAuth } from '@/auth/store';
import { InkCanvas } from '@/components/ink-canvas';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { localPageUri } from '@/offline/bundles';

export default function WriteScreen() {
  const { attempt, page } = useLocalSearchParams<{
    attempt: string;
    page: string;
  }>();
  const attemptId = Number(attempt);
  const pageId = Number(page);
  const { isStudent } = useAuth();

  const { data: attemptData, isLoading } = useQuery({
    queryKey: ['attempt', attemptId],
    queryFn: () => api.attempt(attemptId),
  });

  const worksheet = attemptData?.worksheet;

  // Bundle carries short-lived presigned image URLs for online viewing.
  const { data: bundle } = useQuery({
    queryKey: ['worksheet', worksheet?.id],
    queryFn: () => api.worksheetBundle(worksheet!.id),
    enabled: !!worksheet,
  });

  const pageIndex = worksheet?.pages.findIndex((p) => p.id === pageId) ?? -1;
  const currentPage =
    pageIndex >= 0 ? worksheet?.pages[pageIndex] : undefined;

  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const imageUri = useMemo(() => {
    if (!worksheet || !currentPage) return null;
    const local = localPageUri(worksheet.id, currentPage.order);
    if (local) return local;
    return (
      bundle?.page_downloads.find((d) => d.order === currentPage.order)?.url ??
      null
    );
  }, [worksheet, currentPage, bundle]);

  const saveAndGo = async (dir: 1 | -1) => {
    if (!worksheet || !currentPage) return;
    setSaving(true);
    try {
      if (strokes.length > 0) {
        await api.uploadStrokes(attemptId, pageId, strokes);
      }
      const next = worksheet.pages[pageIndex + dir];
      if (next) {
        router.setParams({ page: String(next.id) } as never);
        setStrokes([]);
      }
    } finally {
      setSaving(false);
    }
  };

  const submit = async () => {
    if (!currentPage) return;
    setSubmitting(true);
    try {
      if (strokes.length > 0) {
        await api.uploadStrokes(attemptId, pageId, strokes);
      }
      await api.submitAttempt(attemptId);
      Alert.alert(
        'Submitted',
        'Your work has been sent for marking. Check My attempts for results.',
      );
      router.replace('/(app)/attempts' as never);
    } catch (e) {
      Alert.alert(
        'Submit failed',
        e instanceof Error ? e.message : 'Please try again.',
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (isLoading || !worksheet || !currentPage) {
    return (
      <ThemedView style={styles.center}>
        <ActivityIndicator size="large" />
      </ThemedView>
    );
  }

  const editable = isStudent && attemptData?.status === 'in_progress';

  return (
    <ThemedView style={styles.container}>
      <Stack.Screen
        options={{
          title: `${worksheet.title} — p${currentPage.order + 1}`,
        }}
      />

      <View style={styles.page}>
        {imageUri && (
          <Image
            source={{ uri: imageUri }}
            style={styles.pageImage}
            resizeMode="contain"
          />
        )}
        {!imageUri && (
          <ThemedText type="small" style={styles.offlineNote}>
            Page image unavailable — download the worksheet or go online.
          </ThemedText>
        )}
        <InkCanvas
          strokes={strokes}
          onChange={setStrokes}
          readonly={!editable}
        />
      </View>

      <View style={styles.toolbar}>
        <Pressable
          style={styles.toolButton}
          onPress={() => setStrokes(strokes.slice(0, -1))}
          disabled={!editable || strokes.length === 0}
        >
          <ThemedText type="small">Undo</ThemedText>
        </Pressable>
        <Pressable
          style={styles.toolButton}
          onPress={() => setStrokes([])}
          disabled={!editable || strokes.length === 0}
        >
          <ThemedText type="small">Clear</ThemedText>
        </Pressable>
        <View style={styles.spacer} />
        <Pressable
          style={styles.toolButton}
          onPress={() => saveAndGo(-1)}
          disabled={saving || pageIndex <= 0}
        >
          <ThemedText type="small">← Prev</ThemedText>
        </Pressable>
        <ThemedText type="small">
          {pageIndex + 1} / {worksheet.pages.length}
        </ThemedText>
        <Pressable
          style={styles.toolButton}
          onPress={() => saveAndGo(1)}
          disabled={saving || pageIndex >= worksheet.pages.length - 1}
        >
          <ThemedText type="small">Next →</ThemedText>
        </Pressable>
        {editable && (
          <Pressable
            style={[styles.toolButton, styles.submitButton]}
            onPress={submit}
            disabled={submitting}
          >
            {submitting ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <ThemedText style={styles.submitText}>Submit</ThemedText>
            )}
          </Pressable>
        )}
      </View>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  center: { flex: 1, justifyContent: 'center' },
  page: { flex: 1, backgroundColor: '#fff', position: 'relative' },
  pageImage: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    width: '100%',
    height: '100%',
  },
  offlineNote: { margin: Spacing.four, textAlign: 'center' },
  toolbar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    padding: Spacing.two,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: '#ccc',
  },
  toolButton: { padding: Spacing.two },
  spacer: { flex: 1 },
  submitButton: {
    backgroundColor: '#208AEF',
    borderRadius: 8,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  submitText: { color: '#fff', fontWeight: '700' },
});
