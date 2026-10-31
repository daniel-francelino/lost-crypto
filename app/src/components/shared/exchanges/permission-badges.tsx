import { Check, X } from "lucide-react";
import { type Permissions, permissionItems } from "@/lib/shared/exchanges/connections.api";

export function PermissionBadges({ permissions }: { permissions: Permissions }) {
  return (
    <ul className="flex flex-wrap gap-1.5" aria-label="Permissões da chave">
      {permissionItems(permissions).map((item) => (
        <li
          key={item.key}
          className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-xs ${
            item.ok ? "border-success/40 text-success" : "border-destructive/50 text-destructive"
          }`}
        >
          {item.ok ? (
            <Check className="size-3" aria-hidden="true" />
          ) : (
            <X className="size-3" aria-hidden="true" />
          )}
          <span>{item.text}</span>
        </li>
      ))}
    </ul>
  );
}
