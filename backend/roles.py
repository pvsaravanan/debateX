from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class RoleAssignment:
    """Dataclass holding the allocated roles and their corresponding system prompts."""
    reasoners: List[str] = field(default_factory=list)
    fact_checker: str = ""
    devils_advocate: str = ""
    steelmanner: str = ""
    chairman: str = ""
    system_prompts: Dict[str, str] = field(default_factory=dict)
    chairman_prompt: str = ""


# Human-readable labels for UI display
ROLE_LABELS = {
    "chairman": "Chairman",
    "devils_advocate": "Devil's Advocate",
    "fact_checker": "Fact-Checker",
    "steelmanner": "Steelmanner",
    "reasoner": "Reasoner",
}


# Specialized cognitive prompt templates by Role and Query Type
PROMPT_TEMPLATES = {
    "chairman": {
        "technical": (
            "You are the Chairman of a technical engineering council. Your role is to moderate, "
            "weigh system architectures and clean code arguments, address the Devil's Advocate's warnings, "
            "and synthesize the definitive, optimal technical solution."
        ),
        "creative": (
            "You are the Chairman of a creative writing board. Your role is to balance flavor, original narrative "
            "style, and cohesive formatting, synthesizing the final masterpiece."
        ),
        "factual": (
            "You are the Chairman of a fact-finding committee. Your role is to evaluate evidentiary weight, "
            "synthesize claims verified by the Fact-Checker, and output a highly reliable, objective synthesis."
        ),
        "ethical": (
            "You are the Chairman of an ethical debate board. Your role is to balance utilitarianism, deontology, "
            "and virtue ethics perspectives, synthesizing a balanced and well-reasoned moral overview."
        ),
        "math": (
            "You are the Chairman of a mathematical proofs committee. Your role is to verify logical and axiom "
            "soundness step-by-step, producing the definitive mathematical proof."
        ),
    },
    "devils_advocate": {
        "technical": (
            "You are the Devil's Advocate. Your ONLY job is to aggressively challenge the technical solution. "
            "Expose edge cases, memory leaks, performance bottlenecks, and security vulnerabilities."
        ),
        "creative": (
            "You are the Devil's Advocate. Your ONLY job is to critique the narrative. Expose plot clichés, "
            "pacing issues, character inconsistencies, and lack of emotional depth."
        ),
        "factual": (
            "You are the Devil's Advocate. Your ONLY job is to introduce healthy skepticism. Expose cognitive biases, "
            "unverified assumptions, sample size limits, and correlations confused with causation."
        ),
        "ethical": (
            "You are the Devil's Advocate. Your ONLY job is to challenge moral consensus. Expose moral hypocrisy, "
            "unintended consequences, slippery slopes, and conflicting cultural values."
        ),
        "math": (
            "You are the Devil's Advocate. Your ONLY job is to find a counterexample or logical gap. Challenge every "
            "algebraic leap, unstated axiom, or potential division by zero."
        ),
    },
    "fact_checker": {
        "technical": (
            "You are the Fact-Checker. You MUST verify API signatures, library compatibility, deprecation schedules, "
            "and package versions. You get a web search tool to retrieve correct documentation."
        ),
        "creative": (
            "You are the Fact-Checker. You MUST verify historical accuracy, regional slang timelines, geographical "
            "distances, and real-world cultural details. You get a web search tool."
        ),
        "factual": (
            "You are the Fact-Checker. You MUST verify dates, names, historical events, and scientific statistics. "
            "Cross-reference source attributions rigorously using your web search tool."
        ),
        "ethical": (
            "You are the Fact-Checker. You MUST verify legal precedents, citations of philosophical texts, and case "
            "study historical facts using your web search tool."
        ),
        "math": (
            "You are the Fact-Checker. You MUST verify algebraic equations, arithmetic steps, geometric properties, "
            "and standard formula citations using your web search tool."
        ),
    },
    "steelmanner": {
        "technical": (
            "You are the Steelmanner. Your job is to strengthen other engineers' proposals. Find the absolute best "
            "version of their architecture and improve its logic before the final synthesis."
        ),
        "creative": (
            "You are the Steelmanner. Your job is to elevate other writers' ideas. Find the core emotional spark "
            "in their narratives and polish their prose to make it shine."
        ),
        "factual": (
            "You are the Steelmanner. Your job is to improve the arguments of your peers. Expose the strongest "
            "scientific evidence supporting their theories and clarify their presentation."
        ),
        "ethical": (
            "You are the Steelmanner. Your job is to steelman opposing moral viewpoints. Represent their philosophical "
            "foundations in the strongest, most coherent light possible."
        ),
        "math": (
            "You are the Steelmanner. Your job is to repair incomplete mathematical proofs. Complete skipped steps "
            "and clarify proof logic to build the strongest mathematical argument."
        ),
    },
    "reasoner": {
        "technical": (
            "You are the Lead Reasoner. You must think step-by-step to draft a highly optimized, clean, and complete "
            "code implementation addressing all requirements."
        ),
        "creative": (
            "You are the Lead Reasoner. You must think step-by-step to write a highly evocative, rich, and "
            "thoughtfully paced narrative."
        ),
        "factual": (
            "You are the Lead Reasoner. You must draft a highly analytical, well-structured, and chronologically "
            "precise response detailing all relevant facts."
        ),
        "ethical": (
            "You are the Lead Reasoner. You must reason step-by-step through moral dilemmas using robust philosophical "
            "principles, detailing trade-offs."
        ),
        "math": (
            "You are the Lead Reasoner. You must construct a formal, rigorous, step-by-step mathematical proof, "
            "explaining every transition axiomatically."
        ),
    },
}


def allocate_roles(
    models: List[str],
    query_type: str,
    query_index: int = 0
) -> RoleAssignment:
    """
    Allocates council roles to the provided models list, rotates them deterministically
    based on query_index, and constructs specialized system prompts.

    Args:
        models: List of model names/identifiers
        query_type: Type of query ('technical', 'creative', 'factual', 'ethical', 'math')
        query_index: Offset integer to rotate roles deterministically per query

    Returns:
        RoleAssignment dataclass containing roles and corresponding system prompts.
    """
    if not models:
        raise ValueError("Model list cannot be empty.")

    valid_query_types = ["technical", "creative", "factual", "ethical", "math"]
    normalized_query_type = query_type.strip().lower()
    if normalized_query_type not in valid_query_types:
        # Graceful fallback to factual if invalid type provided
        normalized_query_type = "factual"

    n = len(models)
    
    # 1. Deterministic circular shift to rotate roles
    shift = query_index % n
    rotated_models = models[shift:] + models[:shift]

    assignment = RoleAssignment()
    assignment.system_prompts = {}

    # Helper to construct the system prompt for a model/role combination
    def get_prompt(role_key: str) -> str:
        base = PROMPT_TEMPLATES[role_key][normalized_query_type]
        # Append specific tool note for Fact-Checker
        if role_key == "fact_checker":
            base += "\nIMPORTANT: You have access to a web search tool. ALWAYS search to verify claims when in doubt."
        return base

    # 2. Allocate roles dynamically depending on list size
    if n == 1:
        # Solo model gets the Chairman role (which synthesizes everything)
        assignment.chairman = rotated_models[0]
        assignment.system_prompts[rotated_models[0]] = get_prompt("chairman")
    elif n == 2:
        # 2 models: Chairman and Devil's Advocate (classic dialectic)
        assignment.chairman = rotated_models[0]
        assignment.system_prompts[rotated_models[0]] = get_prompt("chairman")
        
        assignment.devils_advocate = rotated_models[1]
        assignment.system_prompts[rotated_models[1]] = get_prompt("devils_advocate")
    elif n == 3:
        # 3 models: Chairman, Devil's Advocate, Reasoner
        assignment.chairman = rotated_models[0]
        assignment.system_prompts[rotated_models[0]] = get_prompt("chairman")
        
        assignment.devils_advocate = rotated_models[1]
        assignment.system_prompts[rotated_models[1]] = get_prompt("devils_advocate")
        
        assignment.reasoners = [rotated_models[2]]
        assignment.system_prompts[rotated_models[2]] = get_prompt("reasoner")
    elif n == 4:
        # 4 models: Chairman, Devil's Advocate, Reasoner, Fact-Checker
        assignment.chairman = rotated_models[0]
        assignment.system_prompts[rotated_models[0]] = get_prompt("chairman")
        
        assignment.devils_advocate = rotated_models[1]
        assignment.system_prompts[rotated_models[1]] = get_prompt("devils_advocate")
        
        assignment.reasoners = [rotated_models[2]]
        assignment.system_prompts[rotated_models[2]] = get_prompt("reasoner")
        
        assignment.fact_checker = rotated_models[3]
        assignment.system_prompts[rotated_models[3]] = get_prompt("fact_checker")
    else:
        # 5 or more models: Full allocation (Chairman, Devil's Advocate, Reasoners, Fact-Checker, Steelmanner)
        assignment.chairman = rotated_models[0]
        assignment.system_prompts[rotated_models[0]] = get_prompt("chairman")
        
        assignment.devils_advocate = rotated_models[1]
        assignment.system_prompts[rotated_models[1]] = get_prompt("devils_advocate")
        
        assignment.fact_checker = rotated_models[2]
        assignment.system_prompts[rotated_models[2]] = get_prompt("fact_checker")
        
        assignment.steelmanner = rotated_models[3]
        assignment.system_prompts[rotated_models[3]] = get_prompt("steelmanner")
        
        # Remaining models all become Reasoners (satisfying the 2-3 models constraint for large lists)
        assignment.reasoners = rotated_models[4:]
        for model in assignment.reasoners:
            assignment.system_prompts[model] = get_prompt("reasoner")

    return assignment


# Directive appended to council personas so every member still produces a
# complete first-round answer (the adversarial framing kicks in during review).
ROUND1_DIRECTIVE = (
    "\n\nIn the initial round, provide your own complete answer to the user's "
    "question through the lens of your role. In later rounds, apply your role "
    "when evaluating and critiquing the other council members' answers."
)


def allocate_personas(
    council: List[str],
    chairman_model: str,
    query_type: str,
    query_index: int = 0
) -> RoleAssignment:
    """
    Allocate adversarial personas to the debate council, with the chairman persona
    assigned to a separately chosen chairman/moderator model.

    Unlike allocate_roles(), the chairman does NOT consume a council seat — every
    council member gets a deliberation persona (Reasoner, Devil's Advocate,
    Fact-Checker, Steelmanner), and the chairman prompt is stored separately in
    `chairman_prompt` for use during the synthesis round.

    Args:
        council: Models participating in rounds 1-4
        chairman_model: Model that synthesizes in the final round
        query_type: 'technical' | 'creative' | 'factual' | 'ethical' | 'math'
        query_index: Offset to rotate council roles deterministically per query

    Returns:
        RoleAssignment with council personas and the chairman prompt.
    """
    if not council:
        raise ValueError("Council list cannot be empty.")

    valid_query_types = ["technical", "creative", "factual", "ethical", "math"]
    normalized = query_type.strip().lower()
    if normalized not in valid_query_types:
        normalized = "factual"

    n = len(council)
    shift = query_index % n
    rotated = council[shift:] + council[:shift]

    assignment = RoleAssignment()
    assignment.chairman = chairman_model
    assignment.chairman_prompt = PROMPT_TEMPLATES["chairman"][normalized]

    def council_prompt(role_key: str) -> str:
        base = PROMPT_TEMPLATES[role_key][normalized]
        if role_key == "fact_checker":
            base += "\nIMPORTANT: Verify every claim you rely on; flag anything you cannot verify."
        return base + ROUND1_DIRECTIVE

    # There must always be at least one Reasoner drafting a straight answer.
    role_order_by_size = {
        1: ["reasoner"],
        2: ["reasoner", "devils_advocate"],
        3: ["reasoner", "devils_advocate", "fact_checker"],
        4: ["reasoner", "devils_advocate", "fact_checker", "steelmanner"],
    }
    roles = role_order_by_size.get(min(n, 4))
    # 5+ members: extras become additional Reasoners
    roles = roles + ["reasoner"] * (n - len(roles))

    for model, role in zip(rotated, roles):
        assignment.system_prompts[model] = council_prompt(role)
        if role == "reasoner":
            assignment.reasoners.append(model)
        elif role == "devils_advocate":
            assignment.devils_advocate = model
        elif role == "fact_checker":
            assignment.fact_checker = model
        elif role == "steelmanner":
            assignment.steelmanner = model

    return assignment


def get_role_map(assignment: RoleAssignment) -> Dict[str, str]:
    """Map each model to its human-readable role label (for UI display)."""
    role_map: Dict[str, str] = {}
    for model in assignment.reasoners:
        role_map[model] = ROLE_LABELS["reasoner"]
    if assignment.devils_advocate:
        role_map[assignment.devils_advocate] = ROLE_LABELS["devils_advocate"]
    if assignment.fact_checker:
        role_map[assignment.fact_checker] = ROLE_LABELS["fact_checker"]
    if assignment.steelmanner:
        role_map[assignment.steelmanner] = ROLE_LABELS["steelmanner"]
    if assignment.chairman and assignment.chairman not in role_map:
        role_map[assignment.chairman] = ROLE_LABELS["chairman"]
    return role_map
