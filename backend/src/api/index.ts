import express from "express";

import MessageResponse from "../interfaces/MessageResponse";
import emojis from "./emojis";
import chat from "./chat";

const router = express.Router();

router.get<{}, MessageResponse>("/", (req, res) => {
  res.json({
    message: "API - 👋🌎🌍🌏",
  });
});

router.use("/chat", chat);

router.use("/emojis", emojis);

export default router;
