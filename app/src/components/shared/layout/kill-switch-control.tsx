import { useMutation, useQueryClient } from "@tanstack/react-query";
import { OctagonX } from "lucide-react";
import { useState } from "react";
import { toast } from "lost-ui/ui/sonner";
import { Button } from "lost-ui/ui/button";
import { ConfirmDialog } from "@/components/shared/feedback/confirm-dialog";
import { DangerButton } from "@/components/shared/feedback/danger-button";
import { useSystemStatus } from "@/hooks/shared/use-system";
import { useSessionUser } from "@/hooks/shared/use-session";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { Capability, can } from "@/lib/shared/capability";
import { formatDateTime } from "@/lib/shared/dates";
import { setKillSwitch } from "@/lib/shared/system/system.api";

export function KillSwitchControl() {
  const user = useSessionUser();
  const status = useSystemStatus();
  const client = useQueryClient();
  const [open, setOpen] = useState(false);

  const mutation = useMutation({
    mutationFn: ({ active, reason }: { active: boolean; reason: string }) =>
      setKillSwitch(active, reason === "" ? null : reason),
    onSuccess: async (_state, variables) => {
      await client.invalidateQueries({ queryKey: QueryKey.System.all() });
      toast.success(variables.active ? "Kill switch ativado." : "Kill switch liberado.");
    },
  });

  if (!can(user, Capability.SystemKillSwitch) || status.data === undefined) return null;
  const active = status.data.kill_switch.active;
  const state = status.data.kill_switch;

  return (
    <>
      {active ? (
        <Button size="sm" variant="outline" onClick={() => setOpen(true)} className="h-8 gap-1.5">
          <OctagonX className="size-4" aria-hidden="true" />
          Liberar kill switch
        </Button>
      ) : (
        <DangerButton size="sm" onClick={() => setOpen(true)} className="h-8 gap-1.5">
          <OctagonX className="size-4" aria-hidden="true" />
          Kill switch
        </DangerButton>
      )}
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        destructive={!active}
        title={active ? "Liberar o kill switch?" : "Ativar o kill switch?"}
        description={
          active
            ? `Ativado em ${formatDateTime(state.changed_at)}${state.reason === null ? "" : ` — motivo: ${state.reason}`}. Liberar não retoma os bots: inicie cada um de novo.`
            : "Todos os bots rodando serão pausados e nenhuma ordem nova será enviada. Stops nativos continuam na exchange."
        }
        confirmLabel={active ? "Liberar" : "Ativar kill switch"}
        reasonLabel={active ? "Motivo da liberação" : "Motivo (opcional)"}
        reasonRequired={active}
        onConfirm={(reason) => mutation.mutateAsync({ active: !active, reason })}
      />
    </>
  );
}
