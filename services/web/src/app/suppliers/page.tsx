import { apiGet } from "../_components/api";

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
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Base URL</th>
                <th className="px-4 py-3">Active</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((s) => (
                <tr key={s.id} className="border-t border-slate-100">
                  <td className="px-4 py-3">{s.id}</td>
                  <td className="px-4 py-3 font-medium">{s.name}</td>
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

