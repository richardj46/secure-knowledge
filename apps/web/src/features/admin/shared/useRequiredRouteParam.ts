import { useParams } from "react-router-dom";

export function useRequiredRouteParam(name: string): string {
  const params = useParams();
  const value = params[name];
  if (!value) {
    throw new Error(`Missing required route parameter: ${name}`);
  }
  return value;
}
