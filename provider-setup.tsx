import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { api, apiErrorText } from "@/src/api";
import { Category, Provider, Service } from "@/src/types";
import { colors, spacing } from "@/src/theme";
import { AppButton, Card, ErrorBox, Field } from "@/src/ui";

type ServiceForm = { categoryId: string; title: string; price: string; description: string };
const blankService = (): ServiceForm => ({ categoryId: "", title: "", price: "", description: "" });

export default function ProviderSetup() {
  const router = useRouter();
  const [categories, setCategories] = useState<Category[]>([]);
  const [displayName, setDisplayName] = useState("");
  const [area, setArea] = useState("");
  const [city, setCity] = useState("Kalna");
  const [mobile, setMobile] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [availableTime, setAvailableTime] = useState("");
  const [services, setServices] = useState<ServiceForm[]>([blankService()]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => { (async () => { try { const c = await api.get<{ data: Category[] }>("/categories"); setCategories(c.data); const p = await api.get<{ data: Provider | null }>("/providers/me/profile"); if (p.data) { setDisplayName(p.data.displayName); setArea(p.data.area); setCity(p.data.city); setMobile(p.data.mobile); setWhatsapp(p.data.whatsapp || ""); setAvailableTime(p.data.availableTime || ""); setServices(p.data.services.map((s: Service) => ({ categoryId: s.categoryId, title: s.title, price: s.price || "", description: s.description || "" }))); } } catch(e) { setError(apiErrorText(e)); } })(); }, []);
  function update(i: number, patch: Partial<ServiceForm>) { setServices(s => s.map((x, idx) => idx === i ? { ...x, ...patch } : x)); }
  async function save() { try { setError(""); setSaving(true); await api.put("/providers/me/profile", { displayName, area, city, mobile, whatsapp, availableTime, services }); router.replace("/(tabs)"); } catch(e) { setError(apiErrorText(e)); } finally { setSaving(false); } }
  return <ScrollView contentContainerStyle={styles.wrap}>
    <Text style={styles.title}>Provider Profile</Text>
    <Field label="Business / Display Name" value={displayName} onChangeText={setDisplayName} />
    <Field label="Area" value={area} onChangeText={setArea} />
    <Field label="City" value={city} onChangeText={setCity} />
    <Field label="Mobile" value={mobile} onChangeText={setMobile} keyboardType="phone-pad" />
    <Field label="WhatsApp (optional)" value={whatsapp} onChangeText={setWhatsapp} keyboardType="phone-pad" />
    <Field label="Available Time" value={availableTime} onChangeText={setAvailableTime} placeholder="10 AM - 8 PM" />
    <Text style={styles.section}>Services & Price</Text>
    {services.map((s, i) => <Card key={i}><Text style={styles.serviceNo}>Service {i + 1}</Text><ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.catRow}>{categories.map(c => <Pressable key={c.id} onPress={() => update(i, { categoryId: c.id, title: s.title || c.name_bn })} style={[styles.cat, s.categoryId === c.id && styles.catA]}><Text style={[styles.catT, s.categoryId === c.id && { color: "#FFF" }]}>{c.icon} {c.name_bn}</Text></Pressable>)}</ScrollView><Field label="Service Title" value={s.title} onChangeText={v => update(i, { title: v })} /><Field label="Price" value={s.price} onChangeText={v => update(i, { price: v })} placeholder="₹100 / negotiable" /><Field label="Description" value={s.description} onChangeText={v => update(i, { description: v })} />{services.length > 1 && <AppButton title="Remove Service" variant="danger" onPress={() => setServices(x => x.filter((_, idx) => idx !== i))} />}</Card>)}
    <AppButton title="Add Another Service" variant="secondary" onPress={() => setServices(s => [...s, blankService()])} />
    {!!error && <ErrorBox message={error} />}
    <AppButton title="Save Provider Profile" onPress={save} loading={saving} />
  </ScrollView>;
}
const styles = StyleSheet.create({ wrap: { padding: spacing.lg, gap: spacing.md, backgroundColor: colors.surface }, title: { fontSize: 26, fontWeight: "900", color: colors.text }, section: { fontSize: 18, fontWeight: "900", color: colors.text, marginTop: spacing.md }, serviceNo: { fontWeight: "900", color: colors.text, marginBottom: spacing.sm }, catRow: { gap: spacing.sm, paddingBottom: spacing.sm }, cat: { backgroundColor: colors.brandSoft, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 8 }, catA: { backgroundColor: colors.brand }, catT: { color: colors.brand, fontWeight: "800" } });
