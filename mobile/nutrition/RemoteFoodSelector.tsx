import { useEffect, useMemo, useRef, useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { useMobileAuth } from "../auth/MobileAuthProvider";
import { createNutritionCatalogueApi, type FoodCatalogueItem } from "./nutritionCatalogueApi";
export function RemoteFoodSelector({ foods, onSelect, selectedFoodId, testID, search, onSearchChange }: {
  foods: readonly FoodCatalogueItem[]; onSelect: (id: string, food?: FoodCatalogueItem) => void;
  selectedFoodId: string | null; testID?: string; searchable?: boolean; search?: string; onSearchChange?: (value: string) => void;
}) {
  const auth = useMobileAuth();
  const api = useMemo(() => createNutritionCatalogueApi(auth.request), [auth.request]);
  const [open, setOpen] = useState(false);
  const [localSearch, setLocalSearch] = useState("");
  const query = search ?? localSearch;
  const [debounced, setDebounced] = useState("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<FoodCatalogueItem[]>([]);
  const [selected, setSelected] = useState<FoodCatalogueItem | null>(null);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const selectedFood = selected?.id === selectedFoodId ? selected : foods.find(f => f.id === selectedFoodId) ?? null;
  const selectionQuery = useRef("");
  useEffect(() => {
    const timer = setTimeout(() => { setDebounced(query.trim()); setPage(1); }, 300);
    return () => clearTimeout(timer);
  }, [query]);
  useEffect(() => {
    if (!open) return;
    let active = true;
    setBusy(true); setError(false);
    if (selectionQuery.current !== debounced || page === 1) setItems([]);
    selectionQuery.current = debounced;
    void api.getFoodCatalogue({ page, pageSize: 40, query: debounced }).then(result => {
      if (!active) return;
      setItems(previous => page === 1 ? result.items : [...previous, ...result.items.filter(item => !previous.some(p => p.id === item.id))]);
      setTotal(result.total);
    }).catch(() => { if (active) setError(true); }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [api, open, debounced, page, attempt]);
  return <View style={{ gap: 8, padding: 8 }}>
    <Pressable testID={testID} accessibilityRole="button" accessibilityLabel={selectedFood ? `ماده غذایی: ${selectedFood.name_fa}` : "انتخاب ماده غذایی"} accessibilityState={{ expanded: open }} onPress={() => setOpen(value => !value)}>
      <Text style={{ color: "#19c8b5", padding: 8 }}>{selectedFood?.name_fa ?? "انتخاب کن…"}</Text>
    </Pressable>
    {open && <>
      <TextInput accessibilityLabel="جست‌وجوی غذا" placeholder="جست‌وجوی غذا" value={query} onChangeText={value => { setLocalSearch(value); onSearchChange?.(value); }} style={{ padding: 10, color: "#eef6f8", borderWidth: 1, borderColor: "#637281" }} />
      {busy && <Text>در حال جست‌وجو…</Text>}
      {error && <Pressable accessibilityRole="button" onPress={() => setAttempt(value => value + 1)}><Text>جست‌وجو ناموفق؛ تلاش دوباره</Text></Pressable>}
      {!busy && !error && !items.length && <Text>غذایی پیدا نشد.</Text>}
      {items.map(food => <Pressable key={food.id} accessibilityRole="button" accessibilityState={{ selected: food.id === selectedFoodId }} onPress={() => { setSelected(food); onSelect(food.id, food); setOpen(false); }}><Text style={{ color: "#eef6f8", padding: 8 }}>{food.name_fa}</Text></Pressable>)}
      {items.length < total && <Pressable accessibilityRole="button" disabled={busy} onPress={() => setPage(value => value + 1)}><Text>نمایش بیشتر</Text></Pressable>}
    </>}
  </View>;
}
