import { Link, useRouter } from "expo-router";
import { useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { api, apiErrorText } from "@/src/api";
import { DishaUser, session } from "@/src/session";
import { colors, spacing } from "@/src/theme";
import { AppButton, ErrorBox, Field } from "@/src/ui";

type AuthRes = { ok: boolean; token: string; user: DishaUser };

export default function Login() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("register");
  const [name, setName] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    try {
      setError("");
      setLoading(true);
      const cleanedIdentifier = identifier.trim();
      const isMobile = /^\d+$/.test(cleanedIdentifier);
      const body = mode === "register"
        ? { name: name.trim(), password, termsAccepted: accepted, ...(isMobile ? { mobile: cleanedIdentifier } : { email: cleanedIdentifier }) }
        : { identifier: cleanedIdentifier, password };
      if (mode === "register" && !accepted) throw new Error("Privacy Policy এবং Terms accept করতে হবে");
      const res = await api.post<AuthRes>(mode === "register" ? "/auth/register" : "/auth/login", body);
      await session.saveToken(res.token);
      await session.saveUser(res.user);
      router.replace(res.user.purpose ? "/(tabs)" : "/purpose");
    } catch (e) {
      setError(apiErrorText(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
      <ScrollView contentContainerStyle={styles.wrap}>
        <Text style={styles.title}>DISHA</Text>
        <Text style={styles.sub}>Local Services OS · ASTRA Technologies</Text>
        <View style={styles.switcher}>
          <Pressable onPress={() => setMode("register")} style={[styles.sw, mode === "register" && styles.swActive]}><Text style={[styles.swT, mode === "register" && styles.swTA]}>Register</Text></Pressable>
          <Pressable onPress={() => setMode("login")} style={[styles.sw, mode === "login" && styles.swActive]}><Text style={[styles.swT, mode === "login" && styles.swTA]}>Login</Text></Pressable>
        </View>
        {mode === "register" && <Field label="Name" value={name} onChangeText={setName} autoCapitalize="words" />}
        <Field label="Email or 10-digit mobile" value={identifier} onChangeText={setIdentifier} keyboardType={/^\d+$/.test(identifier.trim()) ? "phone-pad" : "email-address"} autoCapitalize="none" />
        <Field label="Password" value={password} onChangeText={setPassword} secureTextEntry />
        {mode === "register" && (
          <Pressable onPress={() => setAccepted(!accepted)} style={styles.terms}>
            <Text style={styles.box}>{accepted ? "✓" : ""}</Text>
            <Text style={{ flex: 1, color: colors.muted }}>I agree to Privacy Policy and Terms & Conditions</Text>
          </Pressable>
        )}
        {!!error && <ErrorBox message={error} />}
        <AppButton title={mode === "register" ? "Create Account" : "Login"} onPress={submit} loading={loading} />
        <View style={styles.links}>
          <Link href="/legal/privacy" style={styles.link}>Privacy Policy</Link>
          <Text style={{ color: colors.muted }}>·</Text>
          <Link href="/legal/terms" style={styles.link}>Terms</Link>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
const styles = StyleSheet.create({ wrap: { flexGrow: 1, padding: spacing.xl, justifyContent: "center", gap: spacing.md, backgroundColor: colors.surface }, title: { fontSize: 42, fontWeight: "900", color: colors.brand, textAlign: "center" }, sub: { color: colors.muted, textAlign: "center", marginBottom: spacing.lg }, switcher: { flexDirection: "row", backgroundColor: colors.brandSoft, borderRadius: 18, padding: 4 }, sw: { flex: 1, padding: 12, alignItems: "center", borderRadius: 14 }, swActive: { backgroundColor: colors.brand }, swT: { color: colors.brand, fontWeight: "800" }, swTA: { color: "#FFF" }, terms: { flexDirection: "row", alignItems: "center", gap: spacing.sm }, box: { width: 22, height: 22, borderWidth: 1, borderColor: colors.brand, borderRadius: 6, textAlign: "center", color: colors.brand, fontWeight: "900" }, links: { flexDirection: "row", justifyContent: "center", gap: spacing.sm }, link: { color: colors.brand, fontWeight: "800" } });
