import { useQuery } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { Stack } from 'expo-router/stack';
import { useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';

import { api } from '@/api/client';
import type { Attempt } from '@/api/types';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';

/**
 * Teacher review: shows the AI-suggested mark (when the grader has run) and
 * lets the teacher adjust score + feedback before returning it.
 * Page images are viewable via the worksheet bundle's signed URLs.
 */
export default function ReviewScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const attemptId = Number(id);

  const { data: attempt, isLoading } = useQuery({
    queryKey: ['attempt', attemptId],
    queryFn: () => api.attempt(attemptId),
    refetchInterval: (q) =>
      q.state.data?.status === 'grading' ? 5000 : false,
  });

  if (isLoading || !attempt) {
    return (
      <ThemedView style={styles.center}>
        <ActivityIndicator size="large" />
      </ThemedView>
    );
  }

  const latestJob = attempt.grade_jobs[attempt.grade_jobs.length - 1];

  return (
    <ThemedView style={styles.container}>
      <Stack.Screen options={{ title: `Review — ${attempt.student.username}` }} />
      <ScrollView contentContainerStyle={styles.scroll}>
        <ThemedText type="smallBold" style={styles.title}>
          {attempt.worksheet.title}
        </ThemedText>
        <ThemedText type="small">
          Status: {attempt.status}
          {latestJob ? ` · grader: ${latestJob.status}` : ''}
        </ThemedText>

        {latestJob?.error ? (
          <ThemedText type="small" style={styles.error}>
            Grader error: {latestJob.error}
          </ThemedText>
        ) : null}

        <ThemedText type="smallBold" style={styles.heading}>
          Student work
        </ThemedText>
        {attempt.pages
          .filter((p) => p.url)
          .map((p) => (
            <Image
              key={p.id}
              source={{ uri: p.url! }}
              style={styles.pageImage}
              resizeMode="contain"
            />
          ))}
        {!attempt.pages.some((p) => p.url) && (
          <ThemedText type="small" style={styles.note}>
            Page renders appear here once the grader composites the ink
            (or once pages are uploaded).
          </ThemedText>
        )}

        {attempt.mark?.auto_suggested && (
          <View style={styles.suggestion}>
            <ThemedText type="smallBold">AI suggestion</ThemedText>
            <ThemedText type="small">
              Score {attempt.mark.score} / {attempt.mark.max_score}
            </ThemedText>
            {!!attempt.mark.feedback && (
              <ThemedText type="small">{attempt.mark.feedback}</ThemedText>
            )}
          </View>
        )}

        <MarkForm key={attempt.mark?.id ?? 'none'} attempt={attempt} />
      </ScrollView>
    </ThemedView>
  );
}

function MarkForm({ attempt }: { attempt: Attempt }) {
  const [score, setScore] = useState(
    attempt.mark ? String(attempt.mark.score) : '',
  );
  const [maxScore, setMaxScore] = useState(
    attempt.mark ? String(attempt.mark.max_score) : '',
  );
  const [feedback, setFeedback] = useState(attempt.mark?.feedback ?? '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const returnMarks = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.saveMark(
        attempt.id,
        {
          score: Number(score) || 0,
          max_score: Number(maxScore) || 0,
          feedback,
        },
        attempt.mark?.id,
      );
      await api.returnAttempt(attempt.id);
      router.back();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not return marks');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <ThemedText type="smallBold" style={styles.heading}>
        Final marks
      </ThemedText>
      <View style={styles.row}>
        <TextInput
          style={[styles.input, styles.grow]}
          placeholder="Score"
          keyboardType="numeric"
          value={score}
          onChangeText={setScore}
        />
        <ThemedText type="small">/</ThemedText>
        <TextInput
          style={[styles.input, styles.grow]}
          placeholder="Max"
          keyboardType="numeric"
          value={maxScore}
          onChangeText={setMaxScore}
        />
      </View>
      <TextInput
        style={[styles.input, styles.feedback]}
        placeholder="Feedback for the student"
        multiline
        value={feedback}
        onChangeText={setFeedback}
      />

      {error && (
        <ThemedText type="small" style={styles.error}>
          {error}
        </ThemedText>
      )}

      <Pressable
        style={[styles.button, busy && styles.disabled]}
        onPress={returnMarks}
        disabled={busy || attempt.status === 'returned'}
      >
        {busy ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <ThemedText style={styles.buttonText}>
            {attempt.status === 'returned' ? 'Returned ✓' : 'Confirm & return'}
          </ThemedText>
        )}
      </Pressable>
    </>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  center: { flex: 1, justifyContent: 'center' },
  scroll: { padding: Spacing.three, gap: Spacing.two },
  title: { fontSize: 18 },
  heading: { fontSize: 16, marginTop: Spacing.three },
  pageImage: {
    width: '100%',
    aspectRatio: 1 / Math.SQRT2, // A-portrait pages
    backgroundColor: '#fff',
    borderRadius: 8,
  },
  note: { opacity: 0.7 },
  suggestion: {
    padding: Spacing.three,
    borderRadius: 10,
    backgroundColor: '#ede9fe',
    gap: Spacing.half,
  },
  row: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  grow: { flex: 1 },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    padding: Spacing.two,
    backgroundColor: '#fff',
    color: '#000',
  },
  feedback: { minHeight: 72, textAlignVertical: 'top' },
  error: { color: '#c00' },
  button: {
    backgroundColor: '#208AEF',
    borderRadius: 10,
    padding: Spacing.three,
    alignItems: 'center',
    marginTop: Spacing.two,
  },
  disabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontWeight: '600', fontSize: 16 },
});
