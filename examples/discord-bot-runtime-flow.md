# Discord Bot Runtime Flow

This example shows how a bot wrapper can leave local OMH artifacts while keeping
Hermes Agent as the runtime.

## Flow

1. The bot receives a Discord message.
2. The bot starts a local run artifact:

   ```sh
   omh runtime record --skill oh-my-hermes --harness coding-handling --status started
   ```

3. The bot sends the user request to Hermes Agent.
4. Hermes answers with the installed skill pack available through its normal
   skill discovery.
5. The bot records what it could observe:

   ```sh
   omh runtime delegate --run <run-id> --requested --not-observed --result not_observed
   ```

6. The operator inspects the artifact:

   ```sh
   omh runtime show <run-id>
   ```

## Boundary

Use `--observed` only when the bot or Hermes metadata proves that a separate
specialist lane ran. Otherwise use `not_observed` or `not_available`.
