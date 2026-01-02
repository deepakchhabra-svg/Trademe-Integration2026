import Link from "next/link";
import { apiGet } from "../_components/api";
import { Card, CardHeader, CardTitle, CardContent, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, Play } from "lucide-react";

type Supplier = { id: number; name: string; base_url: string | null; is_active: boolean | null };

export default async function PipelineIndexPage() {
  const suppliers = await apiGet<Supplier[]>("/suppliers");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Pipeline</h1>
          <p className="text-muted-foreground">Manage end-to-end operations by supplier.</p>
        </div>
        <Link href="/ops/trademe">
          <Button variant="outline">Trade Me Health</Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {suppliers.map(s => (
          <Card key={s.id} className="flex flex-col hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg font-bold">{s.name}</CardTitle>
                {s.is_active === false ? <Badge variant="secondary">Inactive</Badge> : <Badge variant="outline" className="text-emerald-600 bg-emerald-50 border-emerald-200">Active</Badge>}
              </div>
              <CardDescription>Supplier ID: {s.id}</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 min-h-[40px]">
              {/* Placeholder for future stats */}
            </CardContent>
            <CardFooter className="gap-2">
              <Link href={`/pipeline/${s.id}`} className="flex-1">
                <Button className="w-full">
                  <Play className="mr-2 h-4 w-4" /> Open Pipeline
                </Button>
              </Link>
              {s.base_url && (
                <a href={s.base_url} target="_blank" rel="noreferrer" title="Visit Site">
                  <Button variant="outline" size="icon">
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                </a>
              )}
            </CardFooter>
          </Card>
        ))}
        {!suppliers.length && (
          <div className="col-span-full py-12 text-center text-muted-foreground border-2 border-dashed rounded-lg bg-muted/50">
            No suppliers found. Check API configuration.
          </div>
        )}
      </div>
    </div>
  )
}
