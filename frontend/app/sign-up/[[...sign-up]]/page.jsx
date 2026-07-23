import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="app-shell grid min-h-screen place-items-center px-4 py-10">
      <div className="flex w-full flex-col items-center">
        <div className="mb-6 max-w-md text-center"><p className="page-kicker">Begin your baseline</p><h1 className="page-title">Create your it'sPEAK workspace</h1><p className="page-summary mx-auto">Build speaking readiness through focused, measurable rehearsals.</p></div>
        <SignUp appearance={{ variables: { colorPrimary: "#2563eb", colorBackground: "var(--surface)", colorInputBackground: "var(--surface-raised)", colorInputText: "var(--text-primary)", colorText: "var(--text-primary)", colorTextSecondary: "var(--text-subtle)", borderRadius: "8px" } }} />
      </div>
    </div>
  );
}
