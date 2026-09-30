import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Stack } from 'expo-router/stack';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';

import { api } from '@/api/client';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useAuth } from '@/auth/store';

export default function DashboardScreen() {
  const { isTeacher, user } = useAuth();
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: api.dashboard,
  });

  return (
    <ThemedView style={styles.container}>
      <Stack.Screen options={{ title: 'Dashboard' }} />
      {isLoading || !data ? (
        <ActivityIndicator style={styles.loader} />
      ) : (
        <>
          <View style={styles.grid}>
            <StatCard label="Attempts" value={data.attempts_total} />
            <StatCard
              label="Awaiting review"
              value={data.submitted_pending_review}
            />
            <StatCard
              label="Avg returned score"
              value={
                data.returned_avg_percent != null
                  ? `${data.returned_avg_percent}%`
                  : '—'
              }
            />
          </View>

          <View style={styles.statusList}>
            {Object.entries(data.attempts_by_status).map(([status, n]) => (
              <ThemedText key={status} type="small">
                {status}: {n}
              </ThemedText>
            ))}
          </View>
        </>
      )}

      {isTeacher && (
        <View style={styles.links}>
          <Pressable onPress={() => router.push('/(app)/admin/marking')}>
            <ThemedText type="linkPrimary">Marking queue →</ThemedText>
          </Pressable>
          <Pressable onPress={() => router.push('/(app)/admin/upload')}>
            <ThemedText type="linkPrimary">Upload a worksheet →</ThemedText>
          </Pressable>
        </View>
      )}
      {user?.role === 'parent' && (
        <ThemedText type="small" style={styles.note}>
          Viewing progress for your children.
        </ThemedText>
      )}
    </ThemedView>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <View style={styles.stat}>
      <ThemedText type="smallBold" style={styles.statValue}>
        {value}
      </ThemedText>
      <ThemedText type="small">{label}</ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: Spacing.three, gap: Spacing.three },
  loader: { marginTop: Spacing.five },
  grid: { flexDirection: 'row', gap: Spacing.two },
  stat: {
    flex: 1,
    padding: Spacing.three,
    borderRadius: 10,
    backgroundColor: '#E0E1E6',
    alignItems: 'center',
    gap: Spacing.half,
  },
  statValue: { fontSize: 24, color: '#208AEF' },
  statusList: { gap: Spacing.half },
  links: { gap: Spacing.two },
  note: { opacity: 0.7 },
});
