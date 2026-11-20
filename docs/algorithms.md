# Algorithms & Cost Model — QueryOpt AI

## 1. Logical Rewrite Rules

### A. Predicate Pushdown
- **Rule**: Move $\sigma_{p}$ below $\pi$ and $\bowtie$ towards the base $Scan(T)$ leaves.
- **Join Rule**: For $\sigma_p(R \bowtie S)$:
  - If $cols(p) \subseteq cols(R)$, rewrite to $\sigma_p(R) \bowtie S$.
  - If $cols(p) \subseteq cols(S)$, rewrite to $R \bowtie \sigma_p(S)$.
- **Benefit**: Drastically reduces cardinality of intermediate relations before expensive joins.

### B. Selection Simplification
- **Rule**: Decompose conjunctive conditions into independent cascading filters:
  $$\sigma_{p_1 \land p_2}(R) \longrightarrow \sigma_{p_1}(\sigma_{p_2}(R))$$
- **Benefit**: Allows parts of multi-clause conditions to be pushed down independently to different relations.

### C. Projection Pushdown
- **Rule**: Push $\pi$ below joins while retaining attributes needed for subsequent join conditions and final output.
- **Benefit**: Drops unused columns from memory early.

### D. Constant Folding
- **Rule**: Statically evaluate compile-time constant expressions:
  $$\sigma_{1 = 1}(R) \longrightarrow R$$
- **Benefit**: Eliminates redundant CPU evaluation during execution.

---

## 2. Cardinality & Selectivity Estimation

- **Equality Filter ($A = c$)**:
  $$Selectivity(A = c) = \frac{1}{|Distinct(A)|}$$
- **Range Filter ($A > c$)**:
  $$Selectivity(A > c) = \frac{Max(A) - c}{Max(A) - Min(A)}$$
- **Conjunction ($p_1 \land p_2$)**:
  $$Selectivity(p_1 \land p_2) = Selectivity(p_1) \times Selectivity(p_2)$$
- **Disjunction ($p_1 \lor p_2$)**:
  $$Selectivity(p_1 \lor p_2) = s_1 + s_2 - (s_1 \times s_2)$$
- **Equi-Join ($R \bowtie_{R.k = S.k} S$)**:
  $$EstimatedRows = \frac{|R| \times |S|}{\max(|Distinct(R.k)|, |Distinct(S.k)|)}$$

---

## 3. Physical Cost Model

Modeled after System R and PostgreSQL cost units:
- `SEQ_PAGE_COST` = 1.0 (Sequential 4KB page fetch)
- `RANDOM_PAGE_COST` = 4.0 (Random 4KB page fetch)
- `CPU_TUPLE_COST` = 0.01 (In-memory tuple processing)
- `CPU_OPERATOR_COST` = 0.0025 (Condition evaluation)
- `HASH_BUILD_COST` = 0.02 (Hash table insertion)

### Access Path Selection: TableScan vs. IndexScan
- **TableScan Cost**:
  $$Cost_{seq} = Pages \times SEQ\_PAGE\_COST + Rows \times CPU\_TUPLE\_COST$$
- **IndexScan Cost**:
  $$Cost_{idx} = \log_2(Rows) \times RANDOM\_PAGE\_COST + Matches \times RANDOM\_PAGE\_COST \times \frac{RowBytes}{PageSize} + Matches \times CPU\_TUPLE\_COST$$
- The optimizer dynamically chooses `IndexScan` whenever $Cost_{idx} < Cost_{seq}$.

### Join Algorithm Selection: HashJoin vs. NestedLoopJoin
- **NestedLoopJoin Cost**:
  $$Cost_{nl} = OuterRows \times CPU\_TUPLE\_COST + OuterRows \times InnerRows \times CPU\_OPERATOR\_COST$$
- **HashJoin Cost**:
  $$Cost_{hash} = (OuterRows + InnerRows) \times CPU\_TUPLE\_COST + InnerRows \times HASH\_BUILD\_COST$$
- HashJoin is chosen when relations are larger and an equi-join key exists.
