// Deprecated shim: prefer importing from "@/views/common/utils/navHook" via useNavigate().
import { useNavigate } from "@/views/common/utils/navHook";

export type OpenReplayParams = {
  taskId: string | number;
  deviceIds?: Array<string | number>;
  scriptIds?: Array<string | number>;
  celeryId?: string;
  newTab?: boolean;
};

export function useReplayRoom() {
  const { buildReplayUrl, openReplayRoom } = useNavigate();
  return { buildReplayUrl, openReplayRoom };
}
