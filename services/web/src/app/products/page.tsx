import { apiGet } from "../_components/api";
import { ProductsClient } from "./ProductsClient";

type PageResponse<T> = { items: T[]; total: number };

export type MasterProductRow = {
  supplier_product_id: number;
  supplier_id: number | null;
  supplier_name: string | null;
  supplier_sku: string;
  title: string | null;
  cost_price: number | null;
  stock_level: number | null;
  source_status: string | null;
  source_category: string | null;
  final_category_id: string | null;
  final_category_name: string | null;
  product_url: string | null;
  images: string[];
  last_scraped_at: string | null;
  enrichment_status: string | null;
  internal_product_id: number | null;
  internal_sku: string | null;
  listing_stage: "draft" | "live" | null;
  blocked_reasons: string[];
};

export default async function ProductsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; per_page?: string; q?: string; supplier_id?: string; source_category?: string; stage?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page || "1"));
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "50")));
  const q = sp.q || "";
  const supplierId = sp.supplier_id || "";
  const sourceCategory = sp.source_category || "";
  const stage = sp.stage || "all";

  const qp = new URLSearchParams();
  qp.set("page", String(page));
  qp.set("per_page", String(perPage));
  if (q) qp.set("q", q);
  if (supplierId) qp.set("supplier_id", supplierId);
  if (sourceCategory) qp.set("source_category", sourceCategory);
  if (stage) qp.set("stage", stage);

  const data = await apiGet<PageResponse<MasterProductRow>>(`/products?${qp.toString()}`);

  return (
    <ProductsClient
      items={data.items}
      total={data.total}
      page={page}
      perPage={perPage}
      q={q}
      supplierId={supplierId}
      sourceCategory={sourceCategory}
      stage={stage}
    />
  );
}

