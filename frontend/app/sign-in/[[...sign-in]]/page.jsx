import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="app-shell grid min-h-screen place-items-center px-4 py-10">
      <div className="flex w-full flex-col items-center">
        <div className="mb-6 max-w-md text-center"><p className="page-kicker">Rehearsal control room</p><h1 className="page-title">Welcome back to it'sPEAK</h1><p className="page-summary mx-auto">Sign in to continue your retained rehearsal history.</p></div>
        <SignIn appearance={{ variables: { colorPrimary: "#2563eb", colorBackground: "var(--surface)", colorInputBackground: "var(--surface-raised)", colorInputText: "var(--text-primary)", colorText: "var(--text-primary)", colorTextSecondary: "var(--text-subtle)", borderRadius: "8px" } }} />
      </div>
    </div>
  );
}
