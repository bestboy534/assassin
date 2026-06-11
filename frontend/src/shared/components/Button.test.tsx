import { render, screen } from "@testing-library/react";
import { Button } from "./Button";

test("renders link and button semantics explicitly", () => {
  const { rerender } = render(<Button>提交</Button>);
  expect(screen.getByRole("button", { name: "提交" })).toBeEnabled();

  rerender(<Button href="/book-a-demo">预约演示</Button>);
  expect(screen.getByRole("link", { name: "预约演示" })).toHaveAttribute(
    "href",
    "/book-a-demo",
  );
});
