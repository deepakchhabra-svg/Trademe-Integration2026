import { apiGet } from "../../_components/api";
import { EnrichedVaultClient } from "./EnrichedVaultClient";

type PageResponse<T> = { items: T[]; total: number };

type EnrichedItem = {
  id: number;
  sku: string;
  title: string | null;
  raw_title?: string | null;
  supplier_product_id: number | null;
  supplier_id: number | null;
  cost_price: number | null;
  enriched_title: string | null;
  enriched_description: string | null;
  has_raw_description?: boolean;
  has_enriched_description?: boolean;
  images?: string[];
  source_category?: string | null;
  final_category_is_default?: boolean;
  final_category_name?: string | null;
  product_url?: string | null;
  sync_status?: string | null;
  enrichment_status?: string | null;
};

export default async function EnrichedVault({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; per_page?: string; q?: string; supplier_id?: string; enrichment?: string; source_category?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page || "1"));
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "50")));
  const q = sp.q || "";
  const supplierId = sp.supplier_id || "";
  const enrichment = sp.enrichment || "";
  const sourceCategory = sp.source_category || "";

  const qp = new URLSearchParams();
  qp.set("page", String(page));
  qp.set("per_page", String(perPage));
  if (q) qp.set("q", q);
  if (supplierId) qp.set("supplier_id", supplierId);
  if (enrichment) qp.set("enrichment", enrichment);
  if (sourceCategory) qp.set("source_category", sourceCategory);

  const data = await apiGet<PageResponse<EnrichedItem>>(`/vaults/enriched?${qp.toString()}`);

  return (
    <EnrichedVaultClient
      items={data.items}
      total={data.total}
      page={page}
      perPage={perPage}
      q={q}
      supplierId={supplierId}
      enrichment={enrichment}
      sourceCategory={sourceCategory}
    />
  );
}
