import { Given, Then } from "@cucumber/cucumber";
import axios from "axios";
import { expect } from "@playwright/test";
import dotenv from "dotenv";

// Cargar las variables de entorno de API
dotenv.config({ path: '.env.api' });

let response: any;

Given("I make a GET request to {string}", async function (endpoint: string) {
  const baseURL = process.env.API_BASEURL || "https://petstore.swagger.io";
  response = await axios.get(`${baseURL}${endpoint}`);
});

Then("the response status should be {int}", function (status: number) {
  expect(response.status).toBe(status);
});

Then("the response should contain {string}", function (key: string) {
  expect(response.data).toHaveProperty(key);
});
