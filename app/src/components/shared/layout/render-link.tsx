import { Link, type LinkProps } from "@tanstack/react-router";
import type { RenderNavLink } from "lost-ui/app/app-nav";

export const renderLink: RenderNavLink = ({ item: _item, href, children, ...rest }) => (
  <Link to={href as NonNullable<LinkProps["to"]>} {...rest}>
    {children}
  </Link>
);
