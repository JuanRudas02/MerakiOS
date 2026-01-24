import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import { ROUTES } from "@/lib/routes";
import LoginPanel from "@/components/LoginPanel";
import RegisterPanel from "@/components/RegisterPanel";

const Login = () => {
  return (
    <>
      <Helmet>
        <title>Ingresar - MerakiOS</title>
        <meta name="description" content="Ingresa a tu cuenta de MerakiOS o crea una nueva para comenzar." />
      </Helmet>
      
      <main className="min-h-screen grid lg:grid-cols-2">
        <section id="login" className="order-1">
          <LoginPanel />
        </section>
        
        <section id="register" className="order-2">
          <RegisterPanel />
        </section>
      </main>
    </>
  );
};

export default Login;
