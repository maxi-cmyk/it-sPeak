import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="app-shell grid min-h-screen place-items-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center"><p className="page-kicker">Start improving</p><h1 className="page-title">Create your it'sPEAK account</h1><p className="page-summary mx-auto">Practise your speaking and see your progress over time.</p></div>
        <SignUp appearance={{ variables: { colorPrimary: "#2563eb", colorBackground: "var(--surface)", colorInputBackground: "var(--surface-raised)", colorInputText: "var(--text-primary)", colorText: "var(--text-primary)", colorTextSecondary: "var(--text-subtle)", borderRadius: "8px" } }} />
      </div>
    </div>
  );
}
