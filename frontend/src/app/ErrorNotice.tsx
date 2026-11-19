import { ApiError } from "../api/client";

/** A generic error with its request ID, so it can be found in server logs (UI-001 §5). */
export function ErrorNotice({ error }: { error: unknown }) {
  if (!error) return null;
  const apiError = error instanceof ApiError ? error : null;
  const text = apiError?.isNetwork ? "The server could not be reached." : apiError ? apiError.message : "Something went wrong.";
  return (
    <p className="error" role="alert">
      {text}
      {apiError && !apiError.isNetwork && <> ({apiError.code})</>}
      {apiError?.requestId && <span className="request-id"> Request ID: {apiError.requestId}</span>}
    </p>
  );
}
