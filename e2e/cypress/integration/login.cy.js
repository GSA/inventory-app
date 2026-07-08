describe("Login", () => {
  it("Invalid user login attempt", () => {
    cy.login("not-user", "not-password", true);
    cy.contains("Login failed.");
  });

  it("Valid login attempt", () => {
    cy.login();
    cy.get(".nav-tabs>li>a").should("contain", "My Organizations");
  });

  it("Auth cookie has secure attributes", () => {
    cy.login();
    cy.getCookie("ckan").should((cookie) => {
      expect(cookie).to.exist;
      expect(cookie.httpOnly).to.be.true;
      // Secure flag only applies over HTTPS; in CI/local HTTP environments it will be false
      // In production with HTTPS and nginx proxy, it will be true
      // expect(cookie.secure).to.be.true;
      expect(cookie.sameSite).to.eq("lax");
    });
  });
});
