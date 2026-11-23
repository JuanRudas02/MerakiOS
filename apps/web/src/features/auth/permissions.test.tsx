import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { RequirePermission } from "./permissions";
import { makeUser, renderWith } from "@/test/utils";
import { PERMISSIONS } from "@/lib/permissions";

describe("RequirePermission", () => {
  it("muestra el contenido cuando el usuario tiene el permiso", () => {
    renderWith(<RequirePermission permission={PERMISSIONS.TASKS_EXECUTE}>contenido</RequirePermission>, {
      user: makeUser([PERMISSIONS.TASKS_EXECUTE]),
    });
    expect(screen.getByText("contenido")).toBeInTheDocument();
  });

  it("muestra el fallback cuando falta el permiso", () => {
    renderWith(
      <RequirePermission permission={PERMISSIONS.TASKS_MANAGE} fallback={<span>sin acceso</span>}>
        contenido
      </RequirePermission>,
      { user: makeUser([PERMISSIONS.TASKS_EXECUTE]) },
    );
    expect(screen.queryByText("contenido")).not.toBeInTheDocument();
    expect(screen.getByText("sin acceso")).toBeInTheDocument();
  });

  it("acepta una lista (cualquiera de los permisos)", () => {
    renderWith(<RequirePermission permission={[PERMISSIONS.META_MANAGE, PERMISSIONS.MARKETING_MANAGE]}>ok</RequirePermission>, {
      user: makeUser([PERMISSIONS.MARKETING_MANAGE], "marketer"),
    });
    expect(screen.getByText("ok")).toBeInTheDocument();
  });
});
