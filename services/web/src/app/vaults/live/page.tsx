import { apiGet } from "../../_components/api";
import { LiveVaultClient } from "./LiveVaultClient";

type PageResponse<T> = { items: T[]; total: number };

type LiveItem = {
  id: number;
  tm_listing_id: string | null;
  internal_product_id: number | null;
  actual_state: string | null;
  lifecycle_state: string | null;
  actual_price: number | null;
  view_count: number | null;
  watch_count: number | null;
  category_id: string | null;
  title?: string | null;
  thumb?: string | null;
  source_category?: string | null;
  last_synced_at: string | null;
};

export default async function LiveVault({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; per_page?: string; q?: string; status?: string; supplier_id?: string; source_category?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page || "1"));
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "50")));
  const q = sp.q || "";
  const status = sp.status || "Live";
  const supplierId = sp.supplier_id || "";
  const sourceCategory = sp.source_category || "";

  const qp = new URLSearchParams();
  qp.set("page", String(page));
  qp.set("per_page", String(perPage));
  if (q) qp.set("q", q);
  qp.set("status", status);
  if (supplierId) qp.set("supplier_id", supplierId);
  if (sourceCategory) qp.set("source_category", sourceCategory);

  const data = await apiGet<PageResponse<LiveItem>>(`/vaults/live?${qp.toString()}`);

  return (
    <LiveVaultClient
      items={data.items}
      total={data.total}
      page={page}
      perPage={perPage}
      q={q}
      status={status}
      supplierId={supplierId}
      sourceCategory={sourceCategory}
    />
  );
}
