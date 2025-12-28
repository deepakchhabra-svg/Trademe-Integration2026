import { apiGet } from "../../_components/api";
import { RawVaultClient } from "./RawVaultClient";

type PageResponse<T> = { items: T[]; total: number };

type RawItem = {
  id: number;
  supplier_id: number | null;
  external_sku: string;
  title: string | null;
  cost_price: number | null;
  stock_level: number | null;
  sync_status: string | null;
  source_category?: string | null;
  enrichment_status?: string | null;
  enriched_title?: string | null;
  product_url: string | null;
  images: string[];
  last_scraped_at: string | null;
};

export default async function RawVault({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; per_page?: string; q?: string; supplier_id?: string; sync_status?: string; source_category?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page || "1"));
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "50")));
  const q = sp.q || "";
  const supplierId = sp.supplier_id || "";
  const syncStatus = sp.sync_status || "";
  const sourceCategory = sp.source_category || "";

  const qp = new URLSearchParams();
  qp.set("page", String(page));
  qp.set("per_page", String(perPage));
  if (q) qp.set("q", q);
  if (supplierId) qp.set("supplier_id", supplierId);
  if (syncStatus) qp.set("sync_status", syncStatus);
  if (sourceCategory) qp.set("source_category", sourceCategory);

  const data = await apiGet<PageResponse<RawItem>>(`/vaults/raw?${qp.toString()}`);

  return (
    <RawVaultClient
      items={data.items}
      total={data.total}
      page={page}
      perPage={perPage}
      q={q}
      supplierId={supplierId}
      syncStatus={syncStatus}
      sourceCategory={sourceCategory}
    />
  );
}
