# Validate at the boundaries

<!-- summary: Validate and parse untrusted input at system edges; trust internal code. -->
<!-- tier: core -->
<!-- category: Foundations -->

Validation belongs at the edges of the system, not scattered through it. Data
crossing a trust boundary — user input, an HTTP request body, a queue message,
an external API response, a file — is untrusted until proven otherwise. Once
validated at the boundary, internal code can trust its own types and stop
re-checking.

**Parse, don't just check.** Convert untrusted input into a typed, validated
value at the boundary, and pass that inward. Downstream code should receive a
`ValidatedOrder`, not a raw map it must re-inspect.

```
# at the HTTP boundary — reject early, with a clear error
schema = Object({
  email: String().email(),
  age:   Integer().min(0).max(150),
})
order = schema.parse(request.body)   # raises on bad input; internal code trusts `order`
```

Use whatever schema/validation idiom your language offers (a schema library,
constructors with invariants, parameterized query builders). The principle is
constant; the tool is not.

**External responses are input too.** A third-party API that "always" returns a
field will one day not. Validate responses at the boundary the same way you
validate user input.

**Whose decision:** what counts as a boundary is a design decision. If unsure
whether a function is internal or a boundary, treat it as a boundary until the
design says otherwise.
