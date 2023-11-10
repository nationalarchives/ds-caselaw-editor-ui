describe("Login Test", () => {
  it("should successfully log in", () => {
    // Visit the login page
    cy.visit(`/accounts/login/`);

    // Enter the username and password
    cy.get("#id_login").type(Cypress.env("USERNAME"));
    cy.get("#id_password").type(Cypress.env("PASSWORD"));

    // Click the login button
    cy.get('button.button-cta:contains("Sign in")').click();

    // Verify successful login
    cy.url().should("not.include", "/login");
  });
});
