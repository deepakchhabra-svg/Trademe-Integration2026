import { apiGet } from "../_components/api";
import Link from "next/link";
import { tableClass, tableHeadClass, tableRowClass } from "../_components/ui";

type Supplier = { id: number; name: string; base_url: string | null; is_active: boolean };

export default async function SuppliersPage() {
  const suppliers = await apiGet<Supplier[]>("/suppliers");

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Suppliers</h1>
        <p className="mt-1 text-sm text-slate-600">Source systems feeding the store.</p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className={tableClass()}>
            <thead className={tableHeadClass()}>
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Base URL</th>
                <th className="px-4 py-3">Active</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((s) => (
                <tr key={s.id} className={tableRowClass()}>
                  <td className="px-4 py-3">
                    <Link className="underline" href={`/suppliers/${s.id}`}>
                      {s.id}
                    </Link>
                  </td>
                  <td className="px-4 py-3 font-medium">
                    <Link className="hover:underline" href={`/suppliers/${s.id}`}>
                      {s.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{s.base_url || "-"}</td>
                  <td className="px-4 py-3">{s.is_active ? "yes" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

