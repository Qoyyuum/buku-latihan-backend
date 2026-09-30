import { useQuery } from '@tanstack/react-query';
import * as DocumentPicker from 'expo-document-picker';
import { File } from 'expo-file-system';
import { fetch as expoFetch } from 'expo/fetch';
import { Stack } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';

import { api } from '@/api/client';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';

/**
 * Worksheet upload flow:
 *   1. pick/create subject, name the worksheet
 *   2. pick a PDF (rasterized server-side) or page images one-by-one
 *   3. each file → presigned PUT straight to R2 → register page
 *   4. optionally attach an answer-sheet file + marking notes
 *   5. publish
 */
export default function UploadScreen() {
  const { data: subjects } = useQuery({
    queryKey: ['subjects'],
    queryFn: api.subjects,
  });

  const [subjectId, setSubjectId] = useState<number | null>(null);
  const [newSubject, setNewSubject] = useState('');
  const [title, setTitle] = useState('');
  const [examYear, setExamYear] = useState('');
  const [source, setSource] = useState('');
  const [notes, setNotes] = useState('');

  const [worksheetId, setWorksheetId] = useState<number | null>(null);
  const [status, setStatus] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const log = (line: string) => setStatus((s) => [...s, line]);

  const ensureWorksheet = async (): Promise<number> => {
    if (worksheetId) return worksheetId;
    let sid = subjectId;
    if (!sid && newSubject.trim()) {
      const created = await api.createSubject(newSubject.trim());
      sid = created.id;
      setSubjectId(sid);
    }
    if (!sid) throw new Error('Pick a subject first');
    const ws = await api.createWorksheet({
      subject: sid,
      title: title.trim() || 'Untitled worksheet',
      exam_year: examYear ? Number(examYear) : null,
      source: source.trim(),
      status: 'draft',
    });
    setWorksheetId(ws.id);
    log(`Created worksheet #${ws.id}`);
    return ws.id;
  };

  const uploadFile = async (
    asset: DocumentPicker.DocumentPickerAsset,
    contentType: string,
  ): Promise<string> => {
    const wid = await ensureWorksheet();
    const { key, upload_url } = await api.uploadUrl(
      wid,
      asset.name,
      contentType,
    );

    // expo/fetch understands expo-file-system File bodies on native;
    // on web the picker gives us a real Blob already.
    const body =
      Platform.OS === 'web'
        ? (asset.file as unknown as Blob)
        : (new File(asset.uri) as unknown as Blob);
    const res = await expoFetch(upload_url, {
      method: 'PUT',
      headers: { 'Content-Type': contentType },
      body,
    });
    if (!res.ok) throw new Error(`Upload failed (${res.status})`);
    return key;
  };

  const pickPdf = async () => {
    const result = await DocumentPicker.getDocumentAsync({
      type: 'application/pdf',
      copyToCacheDirectory: true,
    });
    if (result.canceled || !result.assets?.[0]) return;
    setBusy(true);
    try {
      const asset = result.assets[0];
      log(`Uploading ${asset.name}…`);
      const key = await uploadFile(asset, 'application/pdf');
      const wid = await ensureWorksheet();
      await api.rasterize(wid, key);
      log('PDF uploaded — pages are being generated on the server.');
    } catch (e) {
      log(e instanceof Error ? e.message : 'PDF upload failed');
    } finally {
      setBusy(false);
    }
  };

  const pickImage = async () => {
    const result = await DocumentPicker.getDocumentAsync({
      type: ['image/png', 'image/jpeg'],
      multiple: true,
      copyToCacheDirectory: true,
    });
    if (result.canceled || !result.assets?.length) return;
    setBusy(true);
    try {
      const wid = await ensureWorksheet();
      let order = 0;
      for (const asset of result.assets) {
        const mime = asset.mimeType ?? 'image/png';
        log(`Uploading ${asset.name}…`);
        const key = await uploadFile(asset, mime);
        await api.registerPage(wid, { image_key: key, order });
        order += 1;
      }
      log(`Registered ${order} page(s).`);
    } catch (e) {
      log(e instanceof Error ? e.message : 'Image upload failed');
    } finally {
      setBusy(false);
    }
  };

  const pickAnswerSheet = async () => {
    const result = await DocumentPicker.getDocumentAsync({
      type: ['application/pdf', 'image/png', 'image/jpeg'],
      copyToCacheDirectory: true,
    });
    if (result.canceled || !result.assets?.[0]) return;
    setBusy(true);
    try {
      const asset = result.assets[0];
      const mime = asset.mimeType ?? 'application/octet-stream';
      const key = await uploadFile(asset, mime);
      const wid = await ensureWorksheet();
      await api.registerAnswerSheet(wid, { file_key: key, notes });
      log('Answer sheet attached.');
    } catch (e) {
      log(e instanceof Error ? e.message : 'Answer sheet upload failed');
    } finally {
      setBusy(false);
    }
  };

  const publish = async () => {
    if (!worksheetId) return;
    setBusy(true);
    try {
      await api.updateWorksheet(worksheetId, { status: 'published' });
      setDone(true);
      log('Published ✓ Students can now see it.');
    } catch (e) {
      log(e instanceof Error ? e.message : 'Publish failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <ThemedView style={styles.container}>
      <Stack.Screen options={{ title: 'Upload worksheet' }} />
      <ScrollView contentContainerStyle={styles.scroll}>
        <ThemedText type="smallBold" style={styles.heading}>
          1. Details
        </ThemedText>
        <View style={styles.chips}>
          {subjects?.results.map((s) => (
            <Pressable
              key={s.id}
              style={[styles.chip, subjectId === s.id && styles.chipActive]}
              onPress={() => setSubjectId(s.id)}
            >
              <ThemedText type="small">{s.name}</ThemedText>
            </Pressable>
          ))}
        </View>
        <TextInput
          style={styles.input}
          placeholder="…or new subject name"
          value={newSubject}
          onChangeText={setNewSubject}
        />
        <TextInput
          style={styles.input}
          placeholder="Worksheet title (e.g. SPM 2023 Paper 1)"
          value={title}
          onChangeText={setTitle}
        />
        <View style={styles.row}>
          <TextInput
            style={[styles.input, styles.grow]}
            placeholder="Exam year"
            keyboardType="numeric"
            value={examYear}
            onChangeText={setExamYear}
          />
          <TextInput
            style={[styles.input, styles.grow]}
            placeholder="Source (e.g. SPM, trial)"
            value={source}
            onChangeText={setSource}
          />
        </View>

        <ThemedText type="smallBold" style={styles.heading}>
          2. Pages
        </ThemedText>
        <View style={styles.row}>
          <Pressable style={styles.button} onPress={pickPdf} disabled={busy}>
            <ThemedText style={styles.buttonText}>Pick PDF</ThemedText>
          </Pressable>
          <Pressable style={styles.button} onPress={pickImage} disabled={busy}>
            <ThemedText style={styles.buttonText}>Pick images</ThemedText>
          </Pressable>
        </View>

        <ThemedText type="smallBold" style={styles.heading}>
          3. Answer sheet + marking notes
        </ThemedText>
        <TextInput
          style={[styles.input, styles.notes]}
          placeholder="Marking scheme / answer key notes (used by the auto-grader)"
          multiline
          value={notes}
          onChangeText={setNotes}
        />
        <Pressable
          style={styles.button}
          onPress={pickAnswerSheet}
          disabled={busy}
        >
          <ThemedText style={styles.buttonText}>Attach answer sheet</ThemedText>
        </Pressable>

        <ThemedText type="smallBold" style={styles.heading}>
          4. Publish
        </ThemedText>
        <Pressable
          style={[styles.button, styles.primary, (!worksheetId || done) && styles.disabled]}
          onPress={publish}
          disabled={!worksheetId || done || busy}
        >
          {busy ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <ThemedText style={styles.buttonText}>
              {done ? 'Published ✓' : 'Publish worksheet'}
            </ThemedText>
          )}
        </Pressable>

        {status.length > 0 && (
          <View style={styles.log}>
            {status.map((line, i) => (
              <ThemedText key={i} type="code">
                {line}
              </ThemedText>
            ))}
          </View>
        )}
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: Spacing.three, gap: Spacing.two },
  heading: { fontSize: 16, marginTop: Spacing.three },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  chip: {
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.one,
    borderRadius: 16,
    backgroundColor: '#E0E1E6',
  },
  chipActive: { backgroundColor: '#bcd8f6' },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    padding: Spacing.two,
    backgroundColor: '#fff',
    color: '#000',
  },
  notes: { minHeight: 72, textAlignVertical: 'top' },
  row: { flexDirection: 'row', gap: Spacing.two },
  grow: { flex: 1 },
  button: {
    backgroundColor: '#6b7280',
    borderRadius: 8,
    padding: Spacing.three,
    alignItems: 'center',
    flex: 1,
  },
  primary: { backgroundColor: '#208AEF' },
  disabled: { opacity: 0.5 },
  buttonText: { color: '#fff', fontWeight: '600' },
  log: {
    marginTop: Spacing.three,
    padding: Spacing.two,
    borderRadius: 8,
    backgroundColor: '#111827',
    gap: 2,
  },
});
