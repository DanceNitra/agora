# Voyager — LLM Agent in Game World

## From "Voyager: An Open-Ended Embodied Agent with Large Language Models" (Wang et al., arXiv:2305.16291)

## Three Core Components

### 1. Automatic Curriculum
- **Skill discovery via exploration**: agent finds novel interactions
- **Task generation**: LLM proposes next task based on what agent has learned
- **Gilbreth principle**: decompose complex tasks into teachable skills

### 2. Skill Library
```typescript
interface Skill {
  name: string;           // "mine_copper_ore"
  code: string;           // executable code / action sequence
  embedding: number[];    // for retrieval
  prerequisites: string[];// ["craft_stone_pickaxe"]
  description: string;    // human-readable
}
```
- Skills are **verifiable programs**, not text descriptions
- New skills composed from existing ones
- Retrieval: when task is given, find most relevant existing skills

### 3. Iterative Prompting
- No fine-tuning — pure prompting
- When action fails → LLM gets error message → tries alternative
- Self-verification: "Did the action succeed? Try again with modifications."

## Application to Agora Dungeon

```typescript
class AgentSkillSystem {
  skills: Map<string, Skill>;
  
  async executeTask(task: string): Promise<Result> {
    // 1. Find relevant existing skills
    const relevant = this.findSkills(task);
    
    // 2. If no skill found, generate new one
    if (relevant.length === 0) {
      const newSkill = await this.discoverSkill(task);
      this.skills.set(newSkill.name, newSkill);
      return this.executeSkill(newSkill);
    }
    
    // 3. Execute existing skill with iterative refinement
    return this.executeWithRetry(relevant, task);
  }
  
  async discoverSkill(task: string): Promise<Skill> {
    // LLM proposes action sequence
    // Game executes, returns success/failure
    // Loop until success, then save as skill
  }
}
```

## Key Patterns to Steal
1. **Skills as executable programs**: not just text — verifiable, reusable
2. **Iterative refinement**: LLM receives environment feedback, adjusts
3. **Automatic curriculum**: let LLM propose next learning goal
4. **Skill composition**: complex tasks = sequence of known skills
