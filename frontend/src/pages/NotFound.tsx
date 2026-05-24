import { useNavigate } from "react-router-dom";

const NotFound = () => {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted">
      <div className="text-center">
        <h1 className="mb-4 text-4xl font-bold">404</h1>
        <p className="mb-4 text-xl text-muted-foreground">Page not found</p>
        <button
          onClick={() => navigate("/")}
          className="text-primary underline hover:text-primary/90"
        >
          Return to Home
        </button>
      </div>
    </div>
  );
};

export default NotFound;
